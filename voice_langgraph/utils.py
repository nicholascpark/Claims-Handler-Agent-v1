"""Utilities for the LangGraph voice agent.

Audio processing, WebSocket handling, and other utility functions.
"""

import asyncio
import base64
import json
import ssl
from typing import Optional, Dict, Any, AsyncGenerator
from datetime import datetime, timedelta

import numpy as np
import sounddevice as sd
import pytz
from websockets import WebSocketClientProtocol


class AudioProcessor:
    """Handles audio input/output processing."""
    
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
        self.selected_device: Optional[int] = None
        
    def select_microphone(self) -> bool:
        """Interactive microphone selection."""
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
        self.stream: Optional[sd.OutputStream] = None
        self._lock = asyncio.Lock()
        
    def _output_callback(self, outdata, frames, time_info, status):
        """Callback for audio output stream."""
        if status:
            print(f"Audio output error: {status}")
            
        bytes_needed = frames * self.channels * 2  # 2 bytes per sample for int16
        
        if len(self.buffer) >= bytes_needed:
            # Get data from buffer
            chunk = bytes(self.buffer[:bytes_needed])
            del self.buffer[:bytes_needed]
            
            # Convert to numpy array
            audio_data = np.frombuffer(chunk, dtype=np.int16)
            audio_data = audio_data.reshape(frames, self.channels)
            outdata[:] = audio_data
        else:
            # Not enough data, output silence
            outdata[:] = 0
            
    def start(self):
        """Start audio playback stream."""
        if self.stream is None:
            self.stream = sd.OutputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=self.dtype,
                blocksize=self.chunk_size,
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
            
    def clear_buffer(self):
        """Clear the playback buffer."""
        self.buffer.clear()


class WebSocketManager:
    """Manages WebSocket connection and message handling."""
    
    def __init__(self, url: str, api_key: str):
        self.url = url
        self.api_key = api_key
        self.ws: Optional[WebSocketClientProtocol] = None
        self._is_connected = False
        
    def get_headers(self) -> list:
        """Get WebSocket headers."""
        return [
            ("api-key", self.api_key),
            ("OpenAI-Beta", "realtime=v1")
        ]
        
    def get_ssl_context(self) -> Optional[ssl.SSLContext]:
        """Get SSL context for secure connections."""
        # Create default SSL context for secure WebSocket connections
        return ssl.create_default_context()
        
    async def connect(self) -> WebSocketClientProtocol:
        """Establish WebSocket connection."""
        import websockets
        
        self.ws = await websockets.connect(
            self.url,
            extra_headers=self.get_headers(),
            subprotocols=["realtime"],
            ssl=self.get_ssl_context(),
            ping_interval=20,
            ping_timeout=10,
            close_timeout=5,
            max_size=10_000_000
        )
        self._is_connected = True
        return self.ws
        
    async def send(self, event: Dict[str, Any]):
        """Send event to WebSocket."""
        if self.ws and self._is_connected:
            try:
                await self.ws.send(json.dumps(event))
            except Exception:
                # Connection is closed or invalid
                self._is_connected = False
            
    async def receive(self) -> Dict[str, Any]:
        """Receive and parse WebSocket message."""
        if self.ws:
            message = await self.ws.recv()
            return json.loads(message)
        raise ConnectionError("WebSocket not connected")
        
    async def close(self):
        """Close WebSocket connection."""
        if self.ws:
            self._is_connected = False
            await self.ws.close()
            self.ws = None


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
    """Format claim data into a readable summary."""
    lines = ["📋 Claim Summary:"]
    
    # Claimant info
    claimant = claim_data.get('claimant', {})
    if claimant:
        lines.append("\n👤 Claimant Information:")
        if claimant.get('full_name'):
            lines.append(f"   • Name: {claimant['full_name']}")
        if claimant.get('phone'):
            lines.append(f"   • Phone: {claimant['phone']}")
        if claimant.get('email'):
            lines.append(f"   • Email: {claimant['email']}")
    
    # Property info
    property_info = claim_data.get('property', {})
    if property_info:
        lines.append("\n🏠 Property Information:")
        if property_info.get('address'):
            lines.append(f"   • Address: {property_info['address']}")
        if property_info.get('type'):
            lines.append(f"   • Type: {property_info['type']}")
    
    # Damage info
    damage = claim_data.get('damage', {})
    if damage:
        lines.append("\n⚠️ Damage Information:")
        if damage.get('type'):
            lines.append(f"   • Type: {damage['type']}")
        if damage.get('date'):
            lines.append(f"   • Date: {damage['date']}")
        if damage.get('description'):
            lines.append(f"   • Description: {damage['description']}")
    
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
    if "yesterday" in user_lower:
        target_date = now - timedelta(days=1)
        return {
            "date": target_date.strftime("%Y-%m-%d"),
            "reference": "yesterday"
        }
    elif "today" in user_lower or "this morning" in user_lower or "this afternoon" in user_lower:
        return {
            "date": now.strftime("%Y-%m-%d"),
            "reference": "today"
        }
    elif "last week" in user_lower:
        target_date = now - timedelta(days=7)
        return {
            "date": target_date.strftime("%Y-%m-%d"),
            "reference": "last week"
        }
    elif "two days ago" in user_lower or "2 days ago" in user_lower:
        target_date = now - timedelta(days=2)
        return {
            "date": target_date.strftime("%Y-%m-%d"),
            "reference": "two days ago"
        }
    
    return None
