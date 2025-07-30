/**
 * Utility for generating a subtle loading sound using Web Audio API
 * Creates three short, pleasant beeps to indicate processing
 */

export const generateLoadingSound = () => {
  return new Promise((resolve, reject) => {
    try {
      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      const sampleRate = audioContext.sampleRate;
      const totalDuration = 1.5; // Total duration: 1.5 seconds
      const beepDuration = 0.15; // Each beep: 150ms
      const pauseDuration = 0.25; // Pause between beeps: 250ms
      const frameCount = sampleRate * totalDuration;
      
      const audioBuffer = audioContext.createBuffer(1, frameCount, sampleRate);
      const channelData = audioBuffer.getChannelData(0);
      
      // Parameters for the beeps
      const frequency = 800; // Pleasant, subtle frequency (800 Hz)
      const volume = 0.08; // Very quiet, subtle volume
      
      // Clear the entire buffer first
      for (let i = 0; i < frameCount; i++) {
        channelData[i] = 0;
      }
      
      // Generate three beeps
      for (let beepIndex = 0; beepIndex < 3; beepIndex++) {
        const beepStartTime = beepIndex * (beepDuration + pauseDuration);
        const beepStartFrame = Math.floor(beepStartTime * sampleRate);
        const beepEndFrame = Math.floor((beepStartTime + beepDuration) * sampleRate);
        
        for (let i = beepStartFrame; i < beepEndFrame && i < frameCount; i++) {
          const timeInBeep = (i - beepStartFrame) / sampleRate;
          const timeInBeepNormalized = timeInBeep / beepDuration;
          
          // Create a smooth envelope for each beep (fade in/out)
          let envelope = 1;
          const fadeTime = 0.02; // 20ms fade in/out
          const fadeFrames = fadeTime * sampleRate;
          
          if (i - beepStartFrame < fadeFrames) {
            // Fade in
            envelope = (i - beepStartFrame) / fadeFrames;
          } else if (beepEndFrame - i < fadeFrames) {
            // Fade out
            envelope = (beepEndFrame - i) / fadeFrames;
          }
          
          // Generate sine wave for the beep
          const sample = volume * envelope * Math.sin(2 * Math.PI * frequency * timeInBeep);
          channelData[i] = sample;
        }
      }
      
      // Convert to base64 WAV format
      const wavData = audioBufferToWav(audioBuffer);
      const base64 = arrayBufferToBase64(wavData);
      
      audioContext.close();
      resolve(base64);
    } catch (error) {
      reject(error);
    }
  });
};

// Helper function to convert AudioBuffer to WAV format
const audioBufferToWav = (audioBuffer) => {
  const length = audioBuffer.length;
  const numberOfChannels = audioBuffer.numberOfChannels;
  const sampleRate = audioBuffer.sampleRate;
  const bytesPerSample = 2;
  const blockAlign = numberOfChannels * bytesPerSample;
  const byteRate = sampleRate * blockAlign;
  const dataSize = length * blockAlign;
  const bufferSize = 44 + dataSize;

  const arrayBuffer = new ArrayBuffer(bufferSize);
  const view = new DataView(arrayBuffer);
  
  const writeString = (offset, string) => {
    for (let i = 0; i < string.length; i++) {
      view.setUint8(offset + i, string.charCodeAt(i));
    }
  };

  // WAV header
  writeString(0, 'RIFF');
  view.setUint32(4, bufferSize - 8, true);
  writeString(8, 'WAVE');
  writeString(12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, numberOfChannels, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, byteRate, true);
  view.setUint16(32, blockAlign, true);
  view.setUint16(34, 16, true);
  writeString(36, 'data');
  view.setUint32(40, dataSize, true);

  // Convert audio data
  let offset = 44;
  for (let i = 0; i < length; i++) {
    for (let channel = 0; channel < numberOfChannels; channel++) {
      const sample = Math.max(-1, Math.min(1, audioBuffer.getChannelData(channel)[i]));
      view.setInt16(offset, sample * 0x7FFF, true);
      offset += 2;
    }
  }

  return arrayBuffer;
};

// Helper function to convert ArrayBuffer to base64
const arrayBufferToBase64 = (buffer) => {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
};

// Cache the loading sound to avoid regenerating it
let cachedLoadingSound = null;

export const getLoadingSound = async () => {
  if (!cachedLoadingSound) {
    cachedLoadingSound = await generateLoadingSound();
  }
  return cachedLoadingSound;
};

export const clearLoadingSoundCache = () => {
  cachedLoadingSound = null;
}; 