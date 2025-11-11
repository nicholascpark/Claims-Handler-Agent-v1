"""Utilities for the LangGraph voice agent.

Audio processing, WebSocket handling, and other utility functions.
"""

import asyncio
import atexit
import base64
import json
import ssl
from typing import Optional, Dict, Any, AsyncGenerator
from datetime import datetime, timedelta

import numpy as np
from time import monotonic
# Optional audio dependency; unavailable on many server images
try:
    import sounddevice as sd  # type: ignore
except Exception:
    sd = None  # type: ignore
import pytz
import aiohttp
from aiohttp import ClientSession, ClientWebSocketResponse, WSMsgType


class AudioProcessor:
    """Handles audio input/output processing."""
    
    def __init__(
        self,
        sample_rate: int = 24000,
        channels: int = 1,
        chunk_size: int = 2048,
        dtype: str = "int16"
    ):
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.dtype = dtype
        self.selected_device: Optional[int] = None
        
    def select_microphone(self) -> bool:
        """Interactive microphone selection."""
        if sd is None:
            print("❌ Audio input not available in this environment")
            return False
        try:
            devices = sd.query_devices()
            input_devices = []
            
            for i, device in enumerate(devices):
                if device.get('max_input_channels', 0) > 0:
                    input_devices.append((i, device))
                    
            if not input_devices:
                print("❌ No input devices found")
                return False
            
            # Get default device
            try:
                default_in = sd.default.device[0]
            except:
                default_in = None
            
            print("\n🎤 Available microphones:")
            for idx, (device_id, device) in enumerate(input_devices, 1):
                name = device.get('name', f'Device {device_id}')
                is_default = " [DEFAULT]" if device_id == default_in else ""
                print(f"   {idx}: {name}{is_default}")
            
            # Get user choice
            while True:
                choice = input("Select microphone (Enter for default): ").strip()
                
                if not choice:
                    self.selected_device = None
                    print("✅ Using default microphone")
                    return True
                    
                try:
                    num = int(choice)
                    if 1 <= num <= len(input_devices):
                        device_id, device = input_devices[num - 1]
                        
                        # Test device
                        try:
                            with sd.InputStream(
                                device=device_id,
                                channels=self.channels,
                                samplerate=self.sample_rate,
                                dtype=self.dtype,
                                blocksize=256
                            ):
                                pass
                            
                            self.selected_device = device_id
                            print(f"✅ Selected: {device.get('name')}")
                            return True
                            
                        except Exception as e:
                            print(f"⚠️  Cannot access device: {e}")
                    else:
                        print(f"Please enter 1-{len(input_devices)}")
                        
                except ValueError:
                    print("Please enter a valid number")
                    
        except KeyboardInterrupt:
            print("\n❌ Selection cancelled")
            return False
            
        except Exception as e:
            print(f"❌ Error selecting microphone: {e}")
            return False
    
    async def stream_microphone(self) -> AsyncGenerator[bytes, None]:
        """Stream audio from microphone."""
        if sd is None:
            raise RuntimeError("Audio input not available in this environment")
        loop = asyncio.get_event_loop()
        queue = asyncio.Queue()
        
        def callback(indata, frames, time, status):
            if status:
                print(f"Audio input error: {status}")
            loop.call_soon_threadsafe(queue.put_nowait, bytes(indata))
        
        stream = sd.InputStream(
            device=self.selected_device,
            channels=self.channels,
            samplerate=self.sample_rate,
            dtype=self.dtype,
            blocksize=self.chunk_size,
            callback=callback
        )
        
        with stream:
            while True:
                data = await queue.get()
                if data is None:
                    break
                yield data


class AudioPlayback:
    """Handles audio playback with buffering."""
    
    def __init__(
        self,
        sample_rate: int = 24000,
        channels: int = 1,
        chunk_size: int = 1024,
        dtype: str = "int16"
    ):
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.dtype = dtype
        self.buffer = bytearray()
        self.stream: Optional[Any] = None
        self._lock = asyncio.Lock()
        # Prebuffer to reduce underruns on network jitter (increase to ~600ms)
        bytes_per_second = self.sample_rate * self.channels * 2  # int16 = 2 bytes
        self._min_prebuffer_bytes = int(bytes_per_second * 0.60)
        # Cap jitter buffer to ~2.0s to avoid aggressive trimming that can slur speech
        self._max_buffer_bytes = int(bytes_per_second * 2.0)
        # Playback state: wait until prebuffer threshold is met
        self._started = False
        self._underrun_count = 0
        self._last_state_log_ts = 0.0
        self._chunks_size_logged = 0
        
    def _output_callback(self, outdata, frames, time_info, status):
        """Callback for audio output stream."""
        if status:
            print(f"Audio output error: {status}")
            
        bytes_needed = frames * self.channels * 2  # 2 bytes per sample for int16
        current_len = len(self.buffer)

        # If playback hasn't started, wait for prebuffer to fill to avoid stutter
        if not self._started:
            if current_len < self._min_prebuffer_bytes:
                outdata[:] = 0
                return
            # Prebuffer satisfied; start playback
            self._started = True
            try:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔊 Playback start (prebuffer={current_len} bytes)")
            except Exception:
                pass

        # Normal playback path
        if current_len >= bytes_needed:
            # Get data from buffer
            chunk = bytes(self.buffer[:bytes_needed])
            del self.buffer[:bytes_needed]

            # Convert to numpy array
            audio_data = np.frombuffer(chunk, dtype=np.int16)
            audio_data = audio_data.reshape(frames, self.channels)
            outdata[:] = audio_data
        else:
            # Underrun: output silence and re-enter prebuffering mode
            outdata[:] = 0
            self._started = False
            self._underrun_count += 1
            if self._underrun_count <= 3 or (self._underrun_count % 50 == 0):
                try:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Audio underrun (count={self._underrun_count}, buffer={current_len} bytes)")
                except Exception:
                    pass
            
    def start(self):
        """Start audio playback stream."""
        if sd is None:
            return
        if self.stream is None:
            self.stream = sd.OutputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=self.dtype,
                blocksize=self.chunk_size,
                latency='high',
                callback=self._output_callback
            )
            self.stream.start()
            
    def stop(self):
        """Stop audio playback stream."""
        if self.stream is not None:
            self.stream.stop()
            self.stream.close()
            self.stream = None
            
    async def add_audio(self, audio_data: bytes):
        """Add audio data to playback buffer."""
        async with self._lock:
            self.buffer.extend(audio_data)
            # Bound jitter buffer: avoid trimming audio; log if exceeding cap
            if len(self.buffer) > self._max_buffer_bytes:
                try:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Playback buffer exceeded cap ({len(self.buffer)}>{self._max_buffer_bytes} bytes); allowing growth to prevent slurring")
                except Exception:
                    pass
            # Log size of first few chunks for debugging
            if self._chunks_size_logged < 3:
                try:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🐛 DEBUG: Added audio chunk {len(audio_data)} bytes (buffer={len(self.buffer)} bytes)")
                except Exception:
                    pass
                self._chunks_size_logged += 1
            
    def clear_buffer(self):
        """Clear the playback buffer."""
        self.buffer.clear()
        # Reset startup state so next response prebuffers properly
        self._started = False
        self._underrun_count = 0
        self._chunks_size_logged = 0

    def get_buffer_size_bytes(self) -> int:
        """Return current playback buffer size in bytes."""
        return len(self.buffer)


class WebSocketManager:
    """Manages WebSocket connection and message handling."""
    
    def __init__(self, url: str, api_key: str):
        self.url = url
        self.api_key = api_key
        self.session: Optional[ClientSession] = None
        self.ws: Optional[ClientWebSocketResponse] = None
        self._is_connected = False
        # Best-effort cleanup to reduce "Unclosed client session" warnings on abrupt exits
        atexit.register(self._atexit_close)
        
    def get_headers(self) -> Dict[str, str]:
        """Get WebSocket headers."""
        return {
            "api-key": self.api_key,
            "OpenAI-Beta": "realtime=v1",
        }
        
    def get_ssl_context(self) -> Optional[ssl.SSLContext]:
        """Get SSL context for secure connections."""
        # Create default SSL context for secure WebSocket connections
        return ssl.create_default_context()
        
    async def connect(self) -> ClientWebSocketResponse:
        """Establish WebSocket connection using aiohttp."""
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(timeout=timeout)
        self.ws = await self.session.ws_connect(
            self.url,
            headers=self.get_headers(),
            protocols=["realtime"],
            ssl=self.get_ssl_context(),
            heartbeat=20,
            max_msg_size=10_000_000,
            autoclose=True,
            autoping=True,
        )
        self._is_connected = True
        return self.ws
        
    async def send(self, event: Dict[str, Any]):
        """Send event to WebSocket."""
        if self.ws and self._is_connected:
            try:
                await self.ws.send_str(json.dumps(event))
            except Exception:
                # Connection is closed or invalid
                self._is_connected = False
            
    async def receive(self) -> Dict[str, Any]:
        """Receive and parse WebSocket message."""
        if self.ws:
            msg = await self.ws.receive()
            if msg.type == WSMsgType.TEXT:
                return json.loads(msg.data)
            if msg.type in (WSMsgType.CLOSED, WSMsgType.ERROR):
                raise ConnectionError("WebSocket connection closed or errored")
            # For other message types (e.g., ping/pong/binary), ignore or handle as needed
            return {}
        raise ConnectionError("WebSocket not connected")
        
    async def close(self):
        """Close WebSocket connection."""
        self._is_connected = False
        if self.ws is not None:
            await self.ws.close()
            self.ws = None
        if self.session is not None:
            await self.session.close()
            self.session = None

    def _atexit_close(self):
        """Ensure session is closed at interpreter exit (best-effort)."""
        try:
            if self.session is None and self.ws is None:
                return
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Schedule async close without awaiting
                    loop.create_task(self.close())
                else:
                    loop.run_until_complete(self.close())
            except RuntimeError:
                # No running loop; create a temporary one
                asyncio.run(self.close())
        except Exception:
            # Swallow errors during interpreter shutdown
            pass


def encode_audio(audio_data: bytes) -> str:
    """Encode audio data to base64."""
    return base64.b64encode(audio_data).decode('ascii')


def decode_audio(audio_b64: str) -> bytes:
    """Decode base64 audio data."""
    return base64.b64decode(audio_b64)


def get_timestamp() -> str:
    """Get current timestamp for logging."""
    return datetime.now().strftime('%H:%M:%S')


def format_claim_summary(claim_data: Dict[str, Any]) -> str:
    """Format claim data into a readable summary for PropertyClaim schema."""
    lines = ["📋 Claim Summary:"]
    
    # Claimant info (PropertyClaim.claimant)
    claimant = claim_data.get('claimant', {}) or {}
    if claimant:
        lines.append("\n👤 Claimant Information:")
        if claimant.get('insured_name'):
            lines.append(f"   • Name: {claimant['insured_name']}")
        if claimant.get('insured_phone'):
            lines.append(f"   • Phone: {claimant['insured_phone']}")
        if claimant.get('policy_number'):
            lines.append(f"   • Policy: {claimant['policy_number']}")
    
    # Incident info (PropertyClaim.incident)
    incident = claim_data.get('incident', {}) or {}
    if incident:
        lines.append("\n📍 Incident Details:")
        if incident.get('incident_date'):
            lines.append(f"   • Date: {incident['incident_date']}")
        if incident.get('incident_time'):
            lines.append(f"   • Time: {incident['incident_time']}")
        loc = incident.get('incident_location', {}) or {}
        if loc.get('incident_street_address'):
            lines.append(f"   • Address: {loc['incident_street_address']}")
        if loc.get('incident_zip_code'):
            lines.append(f"   • Zip/Postal: {loc['incident_zip_code']}")
        if incident.get('incident_description'):
            lines.append(f"   • What happened: {incident['incident_description']}")
    
    # Personal Injury (optional)
    injury = claim_data.get('personal_injury') or None
    if isinstance(injury, dict) and injury:
        lines.append("\n🩺 Personal Injury:")
        if injury.get('points_of_impact'):
            lines.append(f"   • Points of impact: {', '.join(injury.get('points_of_impact', []))}")
        if injury.get('injury_description'):
            lines.append(f"   • Description: {injury['injury_description']}")
        if injury.get('severity'):
            lines.append(f"   • Severity: {injury['severity']}")
    
    # Property Damage (optional)
    damage = claim_data.get('property_damage') or None
    if isinstance(damage, dict) and damage:
        lines.append("\n🧱 Property Damage:")
        if damage.get('property_type'):
            lines.append(f"   • Type: {damage['property_type']}")
        if damage.get('points_of_impact'):
            lines.append(f"   • Damaged areas: {', '.join(damage.get('points_of_impact', []))}")
        if damage.get('damage_description'):
            lines.append(f"   • Description: {damage['damage_description']}")
        if damage.get('estimated_damage_severity'):
            lines.append(f"   • Severity: {damage['estimated_damage_severity']}")
    
    # Claim id
    if claim_data.get('claim_id'):
        lines.append("\n📝 Submission:")
        lines.append(f"   • Claim ID: {claim_data['claim_id']}")
    
    return "\n".join(lines)


def print_field_updates(before: Dict[str, Any], after: Dict[str, Any]):
    """Print field updates in a readable format."""
    def flatten_dict(d: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
        """Flatten nested dictionary."""
        items = {}
        for k, v in d.items():
            key = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                items.update(flatten_dict(v, key))
            else:
                items[key] = v
        return items
    
    before_flat = flatten_dict(before)
    after_flat = flatten_dict(after)
    
    all_keys = set(before_flat.keys()) | set(after_flat.keys())
    changes = []
    
    for key in sorted(all_keys):
        before_val = before_flat.get(key)
        after_val = after_flat.get(key)
        
        if before_val != after_val:
            if before_val is None:
                changes.append(f"➕ {key}: {after_val}")
            elif after_val is None:
                changes.append(f"➖ {key}: {before_val} (removed)")
            else:
                changes.append(f"✏️ {key}: {before_val} → {after_val}")
    
    if changes:
        print("🔄 Field updates:")
        for change in changes:
            print(f"   {change}")


def get_current_time_context(timezone: str = "America/Toronto") -> Dict[str, str]:
    """Get current time context for timezone-aware time extraction.
    
    This provides context for when users say relative times like:
    - "yesterday around this time"
    - "last Tuesday at 3pm"
    - "this morning"
    
    Args:
        timezone: Timezone string (e.g., "America/Toronto", "America/New_York")
        
    Returns:
        Dictionary with current time information for context injection
    """
    try:
        tz = pytz.timezone(timezone)
    except pytz.UnknownTimeZoneError:
        # Default to UTC if timezone is unknown
        tz = pytz.UTC
    
    now = datetime.now(tz)
    
    return {
        "current_date": now.strftime("%Y-%m-%d"),
        "current_time": now.strftime("%H:%M"),
        "current_day_of_week": now.strftime("%A"),
        "current_timezone": timezone,
        "iso_timestamp": now.isoformat(),
        "context_string": (
            f"Current date/time: {now.strftime('%A, %B %d, %Y at %I:%M %p')} ({timezone})"
        )
    }


def parse_relative_time(
    user_input: str,
    reference_timezone: str = "America/Toronto"
) -> Optional[Dict[str, str]]:
    """Parse relative time references like 'yesterday', 'last week', etc.
    
    This is a helper for extraction - not a tool call, just context enrichment.
    
    Args:
        user_input: The user's message that may contain relative time references
        reference_timezone: The user's timezone for accurate parsing
        
    Returns:
        Parsed time information if relative time is detected, None otherwise
    """
    try:
        tz = pytz.timezone(reference_timezone)
    except pytz.UnknownTimeZoneError:
        tz = pytz.UTC
    
    now = datetime.now(tz)
    user_lower = user_input.lower()
    
    # Common relative time patterns
    result = {}
    
    # Date parsing
    if "yesterday" in user_lower:
        target_date = now - timedelta(days=1)
        result["date"] = target_date.strftime("%Y-%m-%d")
        result["reference"] = "yesterday"
        
        # Check for time context like "around this time"
        if "around this time" in user_lower or "at this time" in user_lower:
            result["time"] = now.strftime("%H:%M")
            result["time_reference"] = "around this time"
            
    elif "today" in user_lower:
        result["date"] = now.strftime("%Y-%m-%d")
        result["reference"] = "today"
        
        if "this morning" in user_lower:
            result["time"] = "09:00"  # Approximate morning time
            result["time_reference"] = "this morning"
        elif "this afternoon" in user_lower:
            result["time"] = "14:00"  # Approximate afternoon time
            result["time_reference"] = "this afternoon"
        elif "around this time" in user_lower:
            result["time"] = now.strftime("%H:%M")
            result["time_reference"] = "around this time"
            
    elif "last week" in user_lower:
        target_date = now - timedelta(days=7)
        result["date"] = target_date.strftime("%Y-%m-%d")
        result["reference"] = "last week"
        
    elif "two days ago" in user_lower or "2 days ago" in user_lower:
        target_date = now - timedelta(days=2)
        result["date"] = target_date.strftime("%Y-%m-%d")
        result["reference"] = "two days ago"
        
    elif "three days ago" in user_lower or "3 days ago" in user_lower:
        target_date = now - timedelta(days=3)
        result["date"] = target_date.strftime("%Y-%m-%d")
        result["reference"] = "three days ago"
        
    # Time-only patterns
    elif "around this time" in user_lower or "at this time" in user_lower:
        result["time"] = now.strftime("%H:%M")
        result["time_reference"] = "around this time"
    
    return result if result else None
