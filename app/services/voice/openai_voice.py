"""
OpenAI Voice Service

Provides Speech-to-Text (Whisper) and Text-to-Speech capabilities
using OpenAI's audio APIs.
"""

import logging
import io
from typing import Optional, BinaryIO, Union
from pathlib import Path

from openai import OpenAI, AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


class OpenAIVoice:
    """
    OpenAI Voice service for STT and TTS.
    
    Uses:
    - Whisper for Speech-to-Text
    - TTS-1 for Text-to-Speech
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        whisper_model: Optional[str] = None,
        tts_model: Optional[str] = None,
        tts_voice: Optional[str] = None,
        tts_speed: Optional[float] = None,
    ):
        """
        Initialize OpenAI Voice service.
        
        Args:
            api_key: OpenAI API key (default: from settings)
            whisper_model: Whisper model for STT (default: whisper-1)
            tts_model: TTS model (default: tts-1)
            tts_voice: TTS voice (default: alloy)
            tts_speed: TTS speed multiplier (default: 1.0)
        """
        self.api_key = api_key or settings.openai_api_key
        self.whisper_model = whisper_model or settings.whisper_model
        self.tts_model = tts_model or settings.tts_model
        self.tts_voice = tts_voice or settings.tts_voice
        self.tts_speed = tts_speed if tts_speed is not None else settings.tts_speed
        
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable.")
        
        self._client: Optional[OpenAI] = None
        self._async_client: Optional[AsyncOpenAI] = None
    
    @property
    def client(self) -> OpenAI:
        """Get or create synchronous OpenAI client."""
        if self._client is None:
            self._client = OpenAI(api_key=self.api_key)
        return self._client
    
    @property
    def async_client(self) -> AsyncOpenAI:
        """Get or create asynchronous OpenAI client."""
        if self._async_client is None:
            self._async_client = AsyncOpenAI(api_key=self.api_key)
        return self._async_client
    
    def transcribe(
        self,
        audio_data: Union[bytes, BinaryIO, Path, str],
        language: Optional[str] = None,
        prompt: Optional[str] = None,
    ) -> str:
        """
        Transcribe audio to text using Whisper.
        
        Args:
            audio_data: Audio data as bytes, file object, or file path
            language: Language code (optional, auto-detected if not provided)
            prompt: Optional prompt to guide transcription
            
        Returns:
            Transcribed text
        """
        try:
            # Prepare audio file
            if isinstance(audio_data, bytes):
                audio_file = io.BytesIO(audio_data)
                audio_file.name = "audio.wav"
            elif isinstance(audio_data, (str, Path)):
                audio_file = open(audio_data, "rb")
            else:
                audio_file = audio_data
            
            # Call Whisper API
            logger.info(f"Transcribing audio with {self.whisper_model}")
            
            kwargs = {
                "model": self.whisper_model,
                "file": audio_file,
            }
            
            if language:
                kwargs["language"] = language
            if prompt:
                kwargs["prompt"] = prompt
            
            response = self.client.audio.transcriptions.create(**kwargs)
            
            text = response.text.strip()
            logger.info(f"Transcription successful: {len(text)} chars")
            
            return text
            
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise
        finally:
            # Close file if we opened it
            if isinstance(audio_data, (str, Path)) and audio_file:
                audio_file.close()
    
    async def transcribe_async(
        self,
        audio_data: Union[bytes, BinaryIO],
        language: Optional[str] = None,
        prompt: Optional[str] = None,
    ) -> str:
        """
        Async transcribe audio to text using Whisper.
        
        Args:
            audio_data: Audio data as bytes or file object
            language: Language code (optional)
            prompt: Optional prompt to guide transcription
            
        Returns:
            Transcribed text
        """
        try:
            # Prepare audio file
            if isinstance(audio_data, bytes):
                audio_file = io.BytesIO(audio_data)
                audio_file.name = "audio.wav"
            else:
                audio_file = audio_data
            
            logger.info(f"Async transcribing audio with {self.whisper_model}")
            
            kwargs = {
                "model": self.whisper_model,
                "file": audio_file,
            }
            
            if language:
                kwargs["language"] = language
            if prompt:
                kwargs["prompt"] = prompt
            
            response = await self.async_client.audio.transcriptions.create(**kwargs)
            
            text = response.text.strip()
            logger.info(f"Async transcription successful: {len(text)} chars")
            
            return text
            
        except Exception as e:
            logger.error(f"Async transcription failed: {e}")
            raise
    
    def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: Optional[float] = None,
        response_format: str = "mp3",
    ) -> bytes:
        """
        Convert text to speech.
        
        Args:
            text: Text to synthesize
            voice: Voice to use (optional, uses default if not provided)
            speed: Speed multiplier (optional)
            response_format: Output format (mp3, opus, aac, flac, wav, pcm)
            
        Returns:
            Audio data as bytes
        """
        try:
            voice = voice or self.tts_voice
            speed = speed if speed is not None else self.tts_speed
            
            logger.info(f"Synthesizing speech: {len(text)} chars, voice={voice}")
            
            response = self.client.audio.speech.create(
                model=self.tts_model,
                voice=voice,
                input=text,
                speed=speed,
                response_format=response_format,
            )
            
            audio_data = response.content
            logger.info(f"Synthesis successful: {len(audio_data)} bytes")
            
            return audio_data
            
        except Exception as e:
            logger.error(f"Speech synthesis failed: {e}")
            raise
    
    async def synthesize_async(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: Optional[float] = None,
        response_format: str = "mp3",
    ) -> bytes:
        """
        Async convert text to speech.
        
        Args:
            text: Text to synthesize
            voice: Voice to use (optional)
            speed: Speed multiplier (optional)
            response_format: Output format
            
        Returns:
            Audio data as bytes
        """
        try:
            voice = voice or self.tts_voice
            speed = speed if speed is not None else self.tts_speed
            
            logger.info(f"Async synthesizing speech: {len(text)} chars, voice={voice}")
            
            response = await self.async_client.audio.speech.create(
                model=self.tts_model,
                voice=voice,
                input=text,
                speed=speed,
                response_format=response_format,
            )
            
            audio_data = response.content
            logger.info(f"Async synthesis successful: {len(audio_data)} bytes")
            
            return audio_data
            
        except Exception as e:
            logger.error(f"Async speech synthesis failed: {e}")
            raise


# Singleton instance
_voice_service: Optional[OpenAIVoice] = None


def get_voice_service() -> OpenAIVoice:
    """Get or create the voice service singleton."""
    global _voice_service
    if _voice_service is None:
        _voice_service = OpenAIVoice()
    return _voice_service


async def transcribe_audio(
    audio_data: bytes,
    language: Optional[str] = None,
) -> str:
    """
    Convenience function to transcribe audio.
    
    Args:
        audio_data: Audio data as bytes
        language: Language code (optional)
        
    Returns:
        Transcribed text
    """
    service = get_voice_service()
    return await service.transcribe_async(audio_data, language=language)


async def synthesize_speech(
    text: str,
    voice: Optional[str] = None,
) -> bytes:
    """
    Convenience function to synthesize speech.
    
    Args:
        text: Text to synthesize
        voice: Voice to use (optional)
        
    Returns:
        Audio data as bytes
    """
    service = get_voice_service()
    return await service.synthesize_async(text, voice=voice)
