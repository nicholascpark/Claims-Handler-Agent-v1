import asyncio
import httpx
import numpy as np
import soundfile as sf
from io import BytesIO

from config.settings import settings

async def transcribe_audio_stream(audio_data: bytes) -> str:
    """Converts audio data to text using Azure OpenAI REST API."""
    
    # Enhanced validation
    if not validate_audio_quality(audio_data):
        raise ValueError("Audio data appears to be empty or invalid")
    
    url = (
        f"{settings.AZURE_OPENAI_ENDPOINT}openai/deployments/"
        f"{settings.AZURE_STT_DEPLOYMENT_NAME}/audio/transcriptions"
        f"?api-version={settings.AZURE_TTS_API_VERSION}"
    )
    
    headers = {
        "api-key": settings.AZURE_OPENAI_API_KEY,
    }

    # The API expects a file, so we wrap the byte data in a BytesIO object
    # and provide a name. The content type is 'audio/wav'.
    files = {'file': ('temp_audio.wav', audio_data, 'audio/wav')}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, files=files, timeout=30.0)
            response.raise_for_status()  # Raise an exception for bad status codes
            
            result = response.json()
            transcribed_text = result.get("text", "").strip()
            
            # Enhanced validation for transcription result
            if not transcribed_text:
                raise ValueError("No speech detected in audio")
                
            return transcribed_text
        except httpx.RequestError as exc:
            raise Exception(f"An error occurred during speech-to-text request: {exc}")
        except httpx.HTTPStatusError as exc:
            raise Exception(f"Error response {exc.response.status_code} while requesting {exc.request.url!r}: {exc.response.text}")


async def synthesize_speech_stream(text: str) -> bytes:
    """Converts text to speech using Azure OpenAI REST API and returns audio data as bytes."""
    url = (
        f"{settings.AZURE_OPENAI_ENDPOINT}openai/deployments/"
        f"{settings.AZURE_TTS_DEPLOYMENT_NAME}/audio/speech"
        f"?api-version={settings.AZURE_TTS_API_VERSION}"
    )
    
    headers = {
        "Content-Type": "application/json",
        "api-key": settings.AZURE_OPENAI_API_KEY,
    }
    
    data = {
        "model": settings.TTS_VOICE_MODEL,
        "input": text,
        "voice": "alloy" 
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=data, timeout=30.0)
            response.raise_for_status()
            return await response.aread()
        except httpx.RequestError as exc:
            print(f"An error occurred during text-to-speech request: {exc}")
            return b""
        except httpx.HTTPStatusError as exc:
            print(f"Error response {exc.response.status_code} while requesting {exc.request.url!r}: {exc.response.text}")
            return b""

def validate_audio_quality(audio_data: bytes) -> bool:
    """
    Enhanced validation of the audio data quality.
    Checks for proper audio format and minimum duration.
    """
    if not audio_data or len(audio_data) < 1024:  # Minimum 1KB for valid audio
        print(f"Audio validation failed: insufficient data size ({len(audio_data) if audio_data else 0} bytes)")
        return False
    
    try:
        # Try to read the audio data to verify it's valid
        audio_stream = BytesIO(audio_data)
        data, samplerate = sf.read(audio_stream)
        
        print(f"Audio validation - Duration: {len(data)/samplerate:.2f}s, Sample rate: {samplerate}, Channels: {data.shape[1] if len(data.shape) > 1 else 1}")
        
        # Check if audio has sufficient duration (at least 0.1 seconds)
        if len(data) < samplerate * 0.1:
            print(f"Audio validation failed: duration too short ({len(data)/samplerate:.2f}s)")
            return False
            
        # Check if audio has sufficient amplitude (not silence)
        max_amplitude = np.max(np.abs(data))
        print(f"Audio validation - Max amplitude: {max_amplitude:.4f}")
        if max_amplitude < 0.001:  # Lowered threshold for detecting silence
            print(f"Audio validation failed: audio appears to be silent (max amplitude: {max_amplitude:.4f})")
            return False
            
        print("Audio validation passed")
        return True
    except Exception as e:
        # If we can't read the audio, it's probably invalid
        print(f"Audio validation failed with exception: {str(e)}")
        return False

# Example usage for testing
async def main():
    # This is a conceptual test and requires a sample audio file.
    # To run this, you would need 'sample.wav' in your directory.
    try:
        with open("sample.wav", "rb") as f:
            sample_audio = f.read()
        
        # Test transcription
        if validate_audio_quality(sample_audio):
            transcribed_text = await transcribe_audio_stream(sample_audio)
            print(f"Transcribed Text: {transcribed_text}")

            # Test speech synthesis
            if "error" not in transcribed_text.lower():
                audio_bytes = await synthesize_speech_stream(f"You said: {transcribed_text}")
                if audio_bytes:
                    # To play this audio, you'd typically use a library like `sounddevice` or `pyaudio`
                    # For example, using sounddevice and soundfile:
                    data, samplerate = sf.read(BytesIO(audio_bytes))
                    # sd.play(data, samplerate)
                    # sd.wait()
                    print("Speech synthesis was successful.")
                else:
                    print("Speech synthesis failed.")
    except FileNotFoundError:
        print("Create a 'sample.wav' to test the voice functions.")

if __name__ == "__main__":
    asyncio.run(main()) 