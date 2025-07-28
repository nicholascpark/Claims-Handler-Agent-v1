import os
import requests
from dotenv import load_dotenv
import sounddevice as sd
from scipy.io.wavfile import write
import winsound
from config.settings import settings

load_dotenv()

def speech_to_text(filename="output.wav", duration=5, samplerate=44100):
    """Records audio from the microphone and converts it to text using Azure OpenAI REST API."""
    print("Recording...")
    recording = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=2, dtype='int16')
    sd.wait()  # Wait until recording is finished
    print("Recording complete.")
    
    write(filename, samplerate, recording)  # Save as WAV file

    url = (
        f"{settings.AZURE_OPENAI_ENDPOINT}openai/deployments/"
        f"{settings.AZURE_STT_DEPLOYMENT_NAME}/audio/transcriptions"
        f"?api-version={settings.AZURE_TTS_API_VERSION}"
    )
    
    headers = {
        "api-key": settings.AZURE_OPENAI_API_KEY,
    }
    
    with open(filename, 'rb') as f:
        files = {
            'file': (filename, f, 'audio/wav')
        }
        response = requests.post(url, headers=headers, files=files)

    if response.status_code == 200:
        return response.json().get("text", "No text found in response.")
    else:
        error_details = response.text
        print(f"Error: {response.status_code}")
        print(f"Error details: {error_details}")
        return f"An error occurred during speech-to-text conversion: {error_details}"

def text_to_speech(text, output_filename="speech.mp3"):
    """Converts text to speech using Azure OpenAI REST API and saves it to a file."""
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
        "model": settings.AZURE_TTS_DEPLOYMENT_NAME,
        "input": text,
        "voice": "alloy"
    }
    
    response = requests.post(url, headers=headers, json=data, stream=True)

    if response.status_code == 200:
        with open(output_filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024):
                f.write(chunk)
        return f"Text-to-speech conversion successful. Audio saved to {output_filename}"
    else:
        error_details = response.text
        print(f"Error: {response.status_code}")
        print(f"Error details: {error_details}")
        return f"An error occurred during text-to-speech conversion: {error_details}"

if __name__ == "__main__":
    # Test speech-to-text
    recognized_text = speech_to_text()
    print(f"Recognized: {recognized_text}")

    # Test text-to-speech
    if "error" not in recognized_text.lower() and "no speech" not in recognized_text.lower():
        tts_result = text_to_speech(f"You said: {recognized_text}")
        print(tts_result)
        if "successful" in tts_result:
            winsound.PlaySound("speech.mp3", winsound.SND_FILENAME)
    else:
        tts_result = text_to_speech(recognized_text)
        print(tts_result)
        if "successful" in tts_result:
            winsound.PlaySound("speech.mp3", winsound.SND_FILENAME) 