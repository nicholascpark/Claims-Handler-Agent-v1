"""Voice Agent for Claims Handler - Following OpenAI Realtime Agents Pattern

This module implements voice interaction using the junior/supervisor pattern
from the OpenAI Realtime Agents reference implementation.
"""

import asyncio
import json
import os
import base64
import time
import queue
from datetime import datetime
from typing import Dict, List, Any, Optional

# Audio processing imports
try:
    import sounddevice as sd
    import numpy as np
    import websockets
    from websockets.exceptions import ConnectionClosed
except ImportError as e:
    print(f"❌ Missing voice dependencies: {e}")
    print("🔧 Install with: pip install sounddevice numpy websockets")
    raise

from src.agents.realtime_agent import create_claims_realtime_agent
from src.api.responses_api import GetNextResponseFromSupervisor
from src.config.settings import settings, validate_required_settings


class ClaimsVoiceAgent:
    """
    Voice agent implementing the OpenAI realtime agents supervisor pattern.
    
    Key features:
    - Junior agent handles basic interactions via realtime API
    - Supervisor called for complex decisions via getNextResponseFromSupervisor
    - Event-driven conversation flow
    - Audio recording and playback
    """
    
    def __init__(self):
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.session_id: Optional[str] = None
        self.is_recording = False
        self.is_playing = False
        self.conversation_active = False
        
        # Create junior realtime agent
        self.junior_agent = create_claims_realtime_agent()
        
        # Audio configuration
        self.sample_rate = 24000  # 24kHz for high quality
        self.channels = 1  # Mono
        self.dtype = np.int16  # 16-bit PCM
        # Use ~20ms blocks for smoother audio callback timing
        self.chunk_size = 480
        self.selected_input_device = None  # Will be set by user selection
        
        # Audio queues
        self.audio_input_queue = queue.Queue()
        self.audio_output_queue = queue.Queue()
        # Residual buffer for smoother playback (int16 mono bytes)
        self._playback_residual = bytearray()
        
        # Utterance tracking and response sequencing
        self.speech_start_time: Optional[float] = None
        self.speech_bytes_since_start: int = 0
        # Track simple amplitude to filter out low-energy/background noise
        self.speech_energy_since_start: float = 0.0
        self.speech_sample_count: int = 0
        # Mean absolute amplitude threshold (int16 scale). Tune via env MIN_AVG_AMPLITUDE
        self.min_avg_amplitude: int = int(os.getenv("MIN_AVG_AMPLITUDE", "700"))
        # Minimum user speech required to consider it a valid utterance (ms/bytes)
        self.min_speech_duration_ms: int = int(os.getenv("MIN_SPEECH_MS", "350"))
        self.min_speech_bytes: int = int(self.sample_rate * (self.min_speech_duration_ms / 1000.0)) * self.channels * 2
        
        # Track active responses to avoid overlapping response.create calls
        self.active_response_in_progress: bool = False
        self.pending_response_request: bool = False
        
        # Conversation tracking
        self.conversation_history = []
        self.performance_metrics = {
            "session_start_time": None,
            "total_interactions": 0,
            "supervisor_calls": 0,
            "audio_chunks_sent": 0,
            "audio_chunks_received": 0
        }
        
        # Event handlers
        self.event_handlers = {}
        self._setup_event_handlers()
    
    def select_microphone_device(self) -> bool:
        """Allow user to select microphone device before starting"""
        try:
            devices = sd.query_devices()
            input_devices = []
            
            # Filter for input devices
            for i, device in enumerate(devices):
                if device['max_input_channels'] > 0:
                    input_devices.append((i, device))
            
            if not input_devices:
                self.display_system_message("❌ No input devices found!")
                return False
            
            # Display available microphones
            print("\n🎤 MICROPHONE DEVICE SELECTION")
            print("=" * 50)
            print("Available microphone devices:")
            print()
            
            for idx, (device_id, device) in enumerate(input_devices):
                default_marker = " [DEFAULT]" if device_id == sd.default.device[0] else ""
                print(f"   {idx + 1}: {device['name']}{default_marker}")
                print(f"      Device ID: {device_id}")
                print(f"      Max Input Channels: {device['max_input_channels']}")
                print(f"      Default Sample Rate: {device['default_samplerate']}")
                print()
            
            # Get user selection
            while True:
                try:
                    print("Select microphone device (Enter number or press Enter for default):")
                    user_input = input("🎯 Choice: ").strip()
                    
                    if user_input == "":
                        # Use system default
                        self.selected_input_device = None
                        default_device = sd.default.device[0]
                        if default_device is not None:
                            default_name = devices[default_device]['name']
                            self.display_system_message(f"✅ Using default microphone: {default_name}")
                        else:
                            self.display_system_message("✅ Using system default microphone")
                        break
                    
                    selection = int(user_input)
                    if 1 <= selection <= len(input_devices):
                        device_id, device = input_devices[selection - 1]
                        self.selected_input_device = device_id
                        self.display_system_message(f"✅ Selected microphone: {device['name']}")
                        
                        # Test the selected device
                        if self._test_microphone_device(device_id):
                            break
                        else:
                            self.display_system_message("⚠️  Device test failed. Please try another device.")
                            continue
                    else:
                        print(f"❌ Please enter a number between 1 and {len(input_devices)}")
                
                except ValueError:
                    print("❌ Please enter a valid number")
                except KeyboardInterrupt:
                    print("\n❌ Device selection cancelled")
                    return False
            
            print("-" * 50)
            return True
            
        except Exception as e:
            self.display_system_message(f"❌ Device selection error: {e}")
            return False
    
    def _test_microphone_device(self, device_id: int) -> bool:
        """Test if the microphone device is working"""
        try:
            # Try to create a brief test stream
            with sd.InputStream(
                device=device_id,
                samplerate=self.sample_rate,
                channels=1,
                dtype='float32'
            ) as test_stream:
                # Record a tiny bit to test
                test_data = test_stream.read(int(self.sample_rate * 0.1))  # 100ms
                return len(test_data[0]) > 0
                
        except Exception as e:
            self.display_system_message(f"⚠️  Microphone test failed: {e}")
            return False
    
    def _setup_event_handlers(self):
        """Setup event handlers for WebSocket messages"""
        self.event_handlers = {
            "session.created": self._handle_session_created,
            "session.updated": self._handle_session_updated,
            "conversation.item.created": self._handle_conversation_item_created,
            "response.created": self._handle_response_created,
            "response.output_item.added": self._handle_response_output_item_added,
            "response.output_item.done": self._handle_response_output_item_done,
            "response.content_part.added": self._handle_response_content_part_added,
            "response.content_part.done": self._handle_response_content_part_done,
            "response.audio.delta": self._handle_response_audio_delta,
            "response.audio.done": self._handle_response_audio_done,
            "response.audio_transcript.delta": self._handle_response_audio_transcript_delta,
            "response.audio_transcript.done": self._handle_response_audio_transcript_done,
            "response.text.delta": self._handle_response_text_delta,
            "response.text.done": self._handle_response_text_done,
            "response.done": self._handle_response_done,
            "response.function_call.delta": self._handle_function_call_delta,
            "response.function_call.done": self._handle_function_call_done,
            # Handle argument streaming events to avoid unhandled warnings
            "response.function_call_arguments.delta": self._handle_function_call_arguments_delta,
            "response.function_call_arguments.done": self._handle_function_call_arguments_done,
            "input_audio_buffer.committed": self._handle_input_audio_committed,
            "input_audio_buffer.speech_started": self._handle_speech_started,
            "input_audio_buffer.speech_stopped": self._handle_speech_stopped,
            # Whisper incremental transcription events (suppress noisy warnings)
            "conversation.item.input_audio_transcription.delta": self._handle_transcription_delta,
            "conversation.item.input_audio_transcription.completed": self._handle_transcription_completed,
            "rate_limits.updated": self._handle_rate_limits_updated,
            "error": self._handle_error
        }
    
    async def create_session(self) -> Optional[str]:
        """Create ephemeral session with OpenAI Realtime API"""
        try:
            import aiohttp
            import ssl
            
            headers = {
                "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                "Content-Type": "application/json"
            }
            
            session_payload = {
                "model": settings.REALTIME_MODEL,
                "voice": settings.JUNIOR_AGENT_VOICE
            }
            
            # Handle SSL verification for corporate environments
            ssl_context = None
            if os.getenv("OPENAI_DISABLE_SSL_VERIFY", "").lower() == "true":
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                self.display_system_message("⚠️  SSL verification disabled for corporate environment")
            
            # Create connector with SSL configuration
            connector = aiohttp.TCPConnector(ssl=ssl_context) if ssl_context else None
            
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.post(
                    "https://api.openai.com/v1/realtime/sessions",
                    headers=headers,
                    json=session_payload
                ) as response:
                    
                    if response.status == 200:
                        session_data = await response.json()
                        
                        if "client_secret" in session_data:
                            self.session_id = session_data.get("id", "unknown")
                            self.display_system_message(f"✅ Session created: {self.session_id}")
                            return session_data["client_secret"]["value"]
                        else:
                            self.display_system_message("❌ Failed to create session: No client secret")
                            return None
                    else:
                        error_text = await response.text()
                        self.display_system_message(f"❌ Session creation failed: {response.status} - {error_text}")
                        return None
                
        except Exception as e:
            self.display_system_message(f"❌ Session creation error: {e}")
            return None
    
    async def connect_websocket(self, ephemeral_key: str) -> bool:
        """Connect to OpenAI Realtime API WebSocket"""
        try:
            import ssl
            
            # Build WebSocket URL with authorization
            ws_url = f"wss://api.openai.com/v1/realtime?model={settings.REALTIME_MODEL}"
            
            # Create headers dictionary for auth
            headers = [
                ("Authorization", f"Bearer {ephemeral_key}"),
                ("OpenAI-Beta", "realtime=v1")
            ]
            
            self.display_system_message("🔌 Connecting to OpenAI Realtime API...")
            
            # Handle SSL verification for WebSocket in corporate environments
            ssl_context = None
            if os.getenv("OPENAI_DISABLE_SSL_VERIFY", "").lower() == "true":
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
            
            # WebSocket connection with proper headers format
            self.websocket = await websockets.connect(
                ws_url,
                additional_headers=headers,
                ssl=ssl_context,
                ping_interval=20,
                ping_timeout=10
            )
            
            self.display_system_message("✅ WebSocket connected successfully")
            return True
            
        except Exception as e:
            self.display_system_message(f"❌ WebSocket connection error: {e}")
            return False
    
    async def setup_session(self):
        """Setup realtime session with junior agent configuration"""
        try:
            # Get session config from junior agent
            session_config = self.junior_agent.get_session_config()
            
            # Send session update event
            await self.send_event({
                "type": "session.update",
                "session": session_config
            })
            
            self.display_system_message("🔧 Session configured with junior/supervisor pattern")
            
        except Exception as e:
            self.display_system_message(f"❌ Session setup error: {e}")
    
    async def send_event(self, event: Dict[str, Any]):
        """Send event to WebSocket connection"""
        if self.websocket:
            try:
                await self.websocket.send(json.dumps(event))
            except ConnectionClosed:
                self.display_system_message("❌ WebSocket connection closed")
                self.conversation_active = False
    
    async def handle_websocket_messages(self):
        """Handle incoming WebSocket messages"""
        try:
            async for message in self.websocket:
                try:
                    event = json.loads(message)
                    event_type = event.get("type")
                    
                    # Log event for debugging
                    self.log_event("RECEIVED", event_type, event)
                    
                    # Route to appropriate handler
                    if event_type in self.event_handlers:
                        await self.event_handlers[event_type](event)
                    else:
                        self.display_system_message(f"⚠️  Unhandled event: {event_type}")
                        
                except json.JSONDecodeError:
                    self.display_system_message("❌ Invalid JSON received")
                except Exception as e:
                    self.display_system_message(f"❌ Message handling error: {e}")
                    
        except ConnectionClosed:
            self.display_system_message("🔌 WebSocket connection closed")
            self.conversation_active = False
        except Exception as e:
            self.display_system_message(f"❌ WebSocket error: {e}")
            self.conversation_active = False
    
    # Audio handling with device selection
    def start_audio_recording(self):
        """Start continuous audio recording from selected microphone"""
        def audio_callback(indata, frames, time, status):
            if status:
                self.display_system_message(f"⚠️  Audio input status: {status}")
            
            # Feed server VAD continuously while not playing back agent audio
            if self.conversation_active and not self.is_playing:
                audio_data = (indata[:, 0] * 32767).astype(np.int16)
                self.audio_input_queue.put(audio_data.tobytes())
        
        try:
            self.stream_input = sd.InputStream(
                device=self.selected_input_device,  # Use selected device
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype='float32',
                blocksize=self.chunk_size,
                callback=audio_callback
            )
            
            self.stream_input.start()
            self.display_system_message("🎤 Microphone recording started")
            
        except Exception as e:
            self.display_system_message(f"❌ Audio recording error: {e}")
    
    def start_audio_playback(self):
        """Start audio playback for agent responses"""
        def audio_callback(outdata, frames, time, status):
            if status:
                self.display_system_message(f"⚠️  Audio output status: {status}")
            
            try:
                bytes_per_frame = 2 * self.channels  # int16 mono -> 2 bytes
                bytes_needed = frames * bytes_per_frame
                buffer_bytes = bytearray()

                # Use any residual first
                if self._playback_residual:
                    take = min(len(self._playback_residual), bytes_needed)
                    buffer_bytes += self._playback_residual[:take]
                    del self._playback_residual[:take]

                # Pull from queue until we have enough for this callback
                while len(buffer_bytes) < bytes_needed and not self.audio_output_queue.empty():
                    next_chunk = self.audio_output_queue.get_nowait()
                    buffer_bytes += next_chunk

                if len(buffer_bytes) >= bytes_needed:
                    to_play = bytes(buffer_bytes[:bytes_needed])
                    remainder = buffer_bytes[bytes_needed:]
                    if remainder:
                        # Keep exact-byte residual in int16 format; don't rescale
                        self._playback_residual += remainder

                    audio_int16 = np.frombuffer(to_play, dtype=np.int16)
                    outdata[:, 0] = audio_int16.astype(np.float32) / 32767.0
                else:
                    # Not enough data yet; save what we have for the next callback
                    if buffer_bytes:
                        self._playback_residual += buffer_bytes
                    outdata.fill(0)

            except queue.Empty:
                outdata.fill(0)
            except Exception as e:
                self.display_system_message(f"❌ Audio playback error: {e}")
                outdata.fill(0)
        
        try:
            self.stream_output = sd.OutputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype='float32',
                blocksize=self.chunk_size,
                latency='low',
                callback=audio_callback
            )
            
            self.stream_output.start()
            self.display_system_message("🔊 Audio playback started")
            
        except Exception as e:
            self.display_system_message(f"❌ Audio playback error: {e}")
    
    async def send_audio_data(self):
        """Send audio data from microphone to WebSocket"""
        while self.conversation_active:
            try:
                # Drain a few chunks per cycle to keep up with realtime
                drained = 0
                while not self.audio_input_queue.empty() and drained < 3:
                    audio_bytes = self.audio_input_queue.get_nowait()
                    # Track how much user audio we have in the current utterance
                    if self.is_recording:
                        self.speech_bytes_since_start += len(audio_bytes)
                        try:
                            audio_int16 = np.frombuffer(audio_bytes, dtype=np.int16)
                            # Accumulate mean absolute amplitude per chunk
                            if audio_int16.size > 0:
                                self.speech_energy_since_start += float(np.mean(np.abs(audio_int16)))
                                self.speech_sample_count += 1
                        except Exception:
                            # Amplitude estimation is best-effort; ignore errors
                            pass
                    audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
                    await self.send_event({
                        "type": "input_audio_buffer.append",
                        "audio": audio_b64
                    })
                    self.performance_metrics["audio_chunks_sent"] += 1
                    drained += 1

                # Sleep approximately one block duration
                await asyncio.sleep(self.chunk_size / self.sample_rate)

            except queue.Empty:
                await asyncio.sleep(self.chunk_size / self.sample_rate)
            except Exception as e:
                self.display_system_message(f"❌ Audio send error: {e}")
                await asyncio.sleep(self.chunk_size / self.sample_rate)
    
    # Event Handlers
    async def _handle_session_created(self, event: Dict[str, Any]):
        """Handle session.created event"""
        session_info = event.get("session", {})
        self.display_system_message(f"🎯 Session created with model: {session_info.get('model', 'unknown')}")
    
    async def _handle_session_updated(self, event: Dict[str, Any]):
        """Handle session.updated event"""
        self.display_system_message("🔄 Session configuration updated")
    
    async def _handle_conversation_item_created(self, event: Dict[str, Any]):
        """Handle conversation.item.created event"""
        item = event.get("item", {})
        role = item.get("role")
        item_type = item.get("type")
        self.display_system_message(f"💬 Conversation item created: {role} {item_type}")
    
    async def _handle_response_created(self, event: Dict[str, Any]):
        """Handle response.created event"""
        response = event.get("response", {})
        self.display_system_message(f"🤖 Agent response started: {response.get('id', 'unknown')}")
        # Mark active response to prevent overlapping response.create
        self.active_response_in_progress = True
    
    async def _handle_response_output_item_added(self, event: Dict[str, Any]):
        """Handle response.output_item.added event"""
        item = event.get("item", {})
        self.display_system_message(f"📝 Response item added: {item.get('type', 'unknown')}")
    
    async def _handle_response_output_item_done(self, event: Dict[str, Any]):
        """Handle response.output_item.done event"""
        item = event.get("item", {})
        self.display_system_message(f"📝 Response item done: {item.get('type', 'unknown')}")

    async def _handle_response_content_part_added(self, event: Dict[str, Any]):
        """Handle response.content_part.added event"""
        part = event.get("part", {})
        self.display_system_message(f"🧩 Content part added: {part.get('type', 'unknown')}")
    
    async def _handle_response_content_part_done(self, event: Dict[str, Any]):
        """Handle response.content_part.done event"""
        part = event.get("part", {})
        self.display_system_message(f"🧩 Content part done: {part.get('type', 'unknown')}")

    async def _handle_response_audio_delta(self, event: Dict[str, Any]):
        """Handle response.audio.delta event"""
        audio_b64 = event.get("delta")
        
        if audio_b64:
            try:
                audio_bytes = base64.b64decode(audio_b64)
                self.audio_output_queue.put(audio_bytes)
                self.performance_metrics["audio_chunks_received"] += 1
                
                if not self.is_playing:
                    self.is_playing = True
                    self.display_voice_status("🔊", "AGENT SPEAKING")
                    
            except Exception as e:
                self.display_system_message(f"❌ Audio decode error: {e}")
    
    async def _handle_response_audio_done(self, event: Dict[str, Any]):
        """Handle response.audio.done event"""
        self.is_playing = False
        self.display_voice_status("🎤", "LISTENING")
        self.display_system_message("✅ Agent finished speaking")
    
    async def _handle_response_audio_transcript_delta(self, event: Dict[str, Any]):
        """Handle response.audio_transcript.delta event (agent TTS transcript)"""
        # Avoid noisy partial output; can be enabled for debugging
        pass
    
    async def _handle_response_audio_transcript_done(self, event: Dict[str, Any]):
        """Handle response.audio_transcript.done event (final agent TTS transcript)"""
        transcript = event.get("transcript", "")
        if transcript:
            self.display_audio_transcript("AGENT", transcript)
    
    async def _handle_response_text_delta(self, event: Dict[str, Any]):
        """Handle response.text.delta event"""
        text_delta = event.get("delta")
        if text_delta:
            print(f"\r🤖 Agent: {text_delta}", end="", flush=True)
    
    async def _handle_response_text_done(self, event: Dict[str, Any]):
        """Handle response.text.done event"""
        text_content = event.get("text", "")
        if text_content:
            self.display_audio_transcript("AGENT", text_content)
    
    async def _handle_response_done(self, event: Dict[str, Any]):
        """Handle response.done event"""
        response = event.get("response", {})
        self.display_system_message(f"✅ Response completed: {response.get('status', 'unknown')}")
        self.performance_metrics["total_interactions"] += 1
        # Clear active response flag and trigger any pending response request
        self.active_response_in_progress = False
        if self.pending_response_request:
            self.pending_response_request = False
            await self.send_event({"type": "response.create"})
    
    async def _handle_function_call_delta(self, event: Dict[str, Any]):
        """Handle response.function_call.delta event"""
        delta = event.get("delta", "")
        if delta:
            print(f"\r🔧 Tool call: {delta}", end="", flush=True)
    
    async def _handle_function_call_done(self, event: Dict[str, Any]):
        """Handle response.function_call.done event - Supervisor tool call"""
        function_call = event.get("function_call", {})
        function_name = function_call.get("name")
        
        if function_name == "getNextResponseFromSupervisor":
            self.performance_metrics["supervisor_calls"] += 1
            self.display_system_message("🧠 Supervisor consulted for decision")
            
            try:
                # Parse arguments
                arguments = json.loads(function_call.get("arguments", "{}"))
                context = arguments.get("relevantContextFromLastUserMessage", "")
                
                # Execute supervisor tool (this happens automatically via OpenAI)
                # The response will come back through normal response events
                self.display_system_message(f"📋 Context sent to supervisor: {context[:50]}...")
                
            except Exception as e:
                self.display_system_message(f"❌ Supervisor call error: {e}")
        else:
            self.display_system_message(f"🔧 Tool call completed: {function_name}")
    
    async def _handle_input_audio_committed(self, event: Dict[str, Any]):
        """Handle input_audio_buffer.committed event"""
        self.display_system_message("📨 User audio committed for processing")
    
    async def _handle_speech_started(self, event: Dict[str, Any]):
        """Handle input_audio_buffer.speech_started event"""
        # If agent is speaking, ignore barge-in to prevent disruptions
        if self.is_playing:
            self.display_system_message("⚠️  Ignoring speech start while agent is speaking (barge-in disabled)")
            return
        self.is_recording = True
        self.speech_start_time = time.time()
        self.speech_bytes_since_start = 0
        self.speech_energy_since_start = 0.0
        self.speech_sample_count = 0
        self.display_voice_status("🎤", "USER SPEAKING")
        self.display_system_message("🎙️  Speech detected - recording started")
    
    async def _handle_speech_stopped(self, event: Dict[str, Any]):
        """Handle input_audio_buffer.speech_stopped event"""
        # If agent is speaking, ignore commit to avoid overlap errors
        if self.is_playing:
            self.display_system_message("⚠️  Ignoring speech stop while agent is speaking (no commit)")
            return
        self.is_recording = False
        self.display_voice_status("⏸️", "PROCESSING")
        self.display_system_message("⏹️  Speech ended - processing...")
        
        # Decide whether to commit based on utterance size and duration
        duration_ms = 0
        if self.speech_start_time is not None:
            duration_ms = int((time.time() - self.speech_start_time) * 1000)
        recorded_bytes = self.speech_bytes_since_start
        self.display_system_message(
            f"📏 Utterance stats — duration: {duration_ms}ms, bytes: {recorded_bytes}, min_required: {self.min_speech_duration_ms}ms/{self.min_speech_bytes} bytes"
        )

        # Guard against empty/too-short utterances (prevents input_audio_buffer_commit_empty)
        if recorded_bytes <= 0 or recorded_bytes < self.min_speech_bytes:
            self.display_system_message("⚠️  Skipping commit: audio too short/noisy")
            return

        # Additional guard: low average amplitude implies background noise
        avg_amp = 0.0
        if self.speech_sample_count > 0:
            avg_amp = self.speech_energy_since_start / float(self.speech_sample_count)
        if avg_amp < self.min_avg_amplitude:
            self.display_system_message(f"⚠️  Skipping commit: low voice energy (avg_amp={avg_amp:.1f} < threshold={self.min_avg_amplitude})")
            return

        # Commit audio buffer
        await self.send_event({"type": "input_audio_buffer.commit"})

        # Trigger response only if there isn't one active; otherwise defer
        if self.active_response_in_progress:
            self.display_system_message("⚠️  Response already in progress — deferring response.create")
            self.pending_response_request = True
        else:
            await self.send_event({"type": "response.create"})
    
    async def _handle_transcription_completed(self, event: Dict[str, Any]):
        """Handle transcription completion"""
        transcript = event.get("transcript", "")
        if transcript:
            self.display_audio_transcript("USER", transcript)

    async def _handle_transcription_delta(self, event: Dict[str, Any]):
        """Handle incremental transcription deltas (suppressed to reduce console noise)"""
        # No-op; keep to prevent "Unhandled event" warnings
        pass

    async def _handle_function_call_arguments_delta(self, event: Dict[str, Any]):
        """Handle streamed function call arguments (delta)"""
        # No-op; suppress unhandled warnings
        pass

    async def _handle_function_call_arguments_done(self, event: Dict[str, Any]):
        """Handle completion of streamed function call arguments"""
        # No-op; suppress unhandled warnings
        pass
    
    async def _handle_rate_limits_updated(self, event: Dict[str, Any]):
        """Handle rate limits updated events"""
        # No-op; available for diagnostics
        pass

    async def _handle_error(self, event: Dict[str, Any]):
        """Handle error events"""
        error_info = event.get("error", {})
        error_message = error_info.get("message", "Unknown error")
        error_code = error_info.get("code", "unknown")
        self.display_system_message(f"❌ API Error [{error_code}]: {error_message}")
        # Proactive recovery for overlapping response errors
        if error_code == "conversation_already_has_active_response":
            # Defer a response request until current one completes
            self.pending_response_request = True
        # Nothing actionable for empty commit besides our guards above
    
    # Display Methods
    def display_banner(self):
        """Display voice agent banner"""
        print("=" * 70)
        print("  CLAIMS HANDLER AGENT v1 - VOICE INTERFACE")
        print("  Junior/Supervisor Pattern - OpenAI Realtime Agents")
        print("=" * 70)
        print(f"Company: {settings.COMPANY_NAME}")
        print(f"Model: {settings.REALTIME_MODEL}")
        print(f"Voice: {settings.JUNIOR_AGENT_VOICE}")
        print(f"Sample Rate: {self.sample_rate}Hz")
        print(f"Pattern: Junior Agent + Supervisor Tool Calls")
        print("=" * 70)
        print()
    
    def display_system_message(self, message: str):
        """Display system message with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"⚙️  [{timestamp}] {message}")
    
    def display_voice_status(self, icon: str, status: str):
        """Display current voice interaction status"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"\n{icon} [{timestamp}] STATUS: {status}")
    
    def display_audio_transcript(self, speaker: str, text: str):
        """Display audio transcript in clear format"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if speaker == "USER":
            print(f"\n🎤 [{timestamp}] You: \"{text}\"")
        elif speaker == "AGENT":
            print(f"\n🤖 [{timestamp}] Agent: \"{text}\"")
        else:
            print(f"\n   [{timestamp}] {speaker}: {text}")
        print()
    
    def log_event(self, direction: str, event_type: str, event_data: Dict[str, Any]):
        """Log WebSocket events for debugging"""
        if os.getenv("DEBUG_VOICE", "").lower() == "true":
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            print(f"🔍 [{timestamp}] {direction}: {event_type}")
    
    def display_performance_metrics(self):
        """Display performance metrics"""
        print("\n" + "=" * 50)
        print("VOICE AGENT PERFORMANCE METRICS")
        print("=" * 50)
        
        if self.performance_metrics["session_start_time"]:
            duration = time.time() - self.performance_metrics["session_start_time"]
            print(f"Session Duration: {duration:.2f}s")
        
        print(f"Total Interactions: {self.performance_metrics['total_interactions']}")
        print(f"Supervisor Calls: {self.performance_metrics['supervisor_calls']}")
        print(f"Audio Chunks Sent: {self.performance_metrics['audio_chunks_sent']}")
        print(f"Audio Chunks Received: {self.performance_metrics['audio_chunks_received']}")
        
        # Calculate supervisor usage percentage
        if self.performance_metrics['total_interactions'] > 0:
            supervisor_percentage = (self.performance_metrics['supervisor_calls'] / 
                                   self.performance_metrics['total_interactions']) * 100
            print(f"Supervisor Usage: {supervisor_percentage:.1f}%")
        
        print("=" * 50)
    
    def display_instructions(self):
        """Display usage instructions"""
        print("🎮 VOICE CONVERSATION INSTRUCTIONS")
        print("=" * 50)
        print("• Speak naturally - the AI will detect when you start/stop")
        print("• Junior agent handles basic greetings and chitchat")
        print("• Complex decisions are escalated to the supervisor automatically")
        print("• Say 'I need to report a claim' to start a claims conversation")
        print("• Use Ctrl+C to stop the conversation anytime")
        print("-" * 50)
        print("🔊 Audio Status Indicators:")
        print("   🎤 USER SPEAKING   - Your voice is being recorded")
        print("   ⏸️  PROCESSING     - AI is processing your speech")
        print("   🤖 AGENT SPEAKING  - AI is responding with voice") 
        print("   🎧 LISTENING      - Ready for your next input")
        print("   🧠 SUPERVISOR      - Complex decision being processed")
        print("-" * 50)
        print()
    
    async def start_voice_conversation(self):
        """Start the main voice conversation loop"""
        try:
            # Validate configuration
            validate_required_settings()
            
            # Display interface
            self.display_banner()
            
            # Select microphone device before starting
            if not self.select_microphone_device():
                self.display_system_message("❌ Cannot proceed without microphone selection")
                return
            
            self.display_instructions()
            
            # Create session
            ephemeral_key = await self.create_session()
            if not ephemeral_key:
                return
            
            # Connect WebSocket
            if not await self.connect_websocket(ephemeral_key):
                return
            
            # Setup session
            await self.setup_session()
            
            # Start audio processing
            self.start_audio_recording()
            self.start_audio_playback()
            
            # Mark conversation as active
            self.conversation_active = True
            self.performance_metrics["session_start_time"] = time.time()
            
            # Display initial status
            self.display_voice_status("🎧", "LISTENING")
            self.display_system_message("Ready for voice conversation with junior/supervisor pattern!")
            
            # Start background tasks
            tasks = [
                asyncio.create_task(self.handle_websocket_messages()),
                asyncio.create_task(self.send_audio_data())
            ]
            
            # Send initial greeting
            await asyncio.sleep(1)
            initial_event = {
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "user", 
                    "content": [{"type": "input_text", "text": "Hello"}]
                }
            }
            await self.send_event(initial_event)
            await self.send_event({"type": "response.create"})
            
            # Wait for tasks
            try:
                await asyncio.gather(*tasks)
            except KeyboardInterrupt:
                self.display_system_message("👋 Conversation interrupted by user")
            
        except Exception as e:
            self.display_system_message(f"❌ Voice conversation error: {e}")
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """Cleanup resources"""
        self.display_system_message("🧹 Cleaning up resources...")
        
        # Stop conversation
        self.conversation_active = False
        
        # Stop audio streams
        try:
            if hasattr(self, 'stream_input'):
                self.stream_input.stop()
                self.stream_input.close()
            if hasattr(self, 'stream_output'):
                self.stream_output.stop()
                self.stream_output.close()
        except:
            pass
        
        # Close WebSocket
        if self.websocket:
            try:
                await self.websocket.close()
            except:
                pass
        
        # Display final metrics
        self.display_performance_metrics()
        
        self.display_system_message("✅ Cleanup completed")


def create_voice_agent() -> ClaimsVoiceAgent:
    """Factory function to create voice agent"""
    return ClaimsVoiceAgent()


async def main():
    """Main entry point for voice agent"""
    voice_agent = create_voice_agent()
    await voice_agent.start_voice_conversation()


if __name__ == "__main__":
    try:
        # Run voice agent (device selection now handled in start_voice_conversation)
        asyncio.run(main())
        
    except KeyboardInterrupt:
        print("\n👋 Voice agent terminated by user")
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("🔧 Install voice dependencies with: pip install sounddevice numpy websockets")
    except Exception as e:
        print(f"❌ Voice agent error: {e}")
        raise

