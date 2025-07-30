/**
 * Utility for generating a subtle loading sound using Web Audio API
 * Creates continuous ambient beeps to indicate processing
 */

export const generateLoadingSound = () => {
  return new Promise((resolve, reject) => {
    try {
      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      const sampleRate = audioContext.sampleRate;
      const totalDuration = 4.0; // Extended duration: 4 seconds for smoother continuity
      const beepDuration = 0.2; // Each beep: 200ms (slightly longer)
      const pauseDuration = 0.8; // Longer pause between beeps: 800ms (slower frequency)
      const frameCount = sampleRate * totalDuration;
      
      const audioBuffer = audioContext.createBuffer(1, frameCount, sampleRate);
      const channelData = audioBuffer.getChannelData(0);
      
      // Parameters for ambient beeps
      const frequency = 440; // Lower, warmer frequency (A4 note - more musical/ambient)
      const volume = 0.06; // Even quieter, more subtle volume
      
      // Clear the entire buffer first
      for (let i = 0; i < frameCount; i++) {
        channelData[i] = 0;
      }
      
      // Generate beeps to fill the duration
      const beepCycleDuration = beepDuration + pauseDuration;
      const numBeeps = Math.floor(totalDuration / beepCycleDuration);
      
      for (let beepIndex = 0; beepIndex < numBeeps; beepIndex++) {
        const beepStartTime = beepIndex * beepCycleDuration;
        const beepStartFrame = Math.floor(beepStartTime * sampleRate);
        const beepEndFrame = Math.floor((beepStartTime + beepDuration) * sampleRate);
        
        for (let i = beepStartFrame; i < beepEndFrame && i < frameCount; i++) {
          const timeInBeep = (i - beepStartFrame) / sampleRate;
          
          // Create a smooth, ambient envelope for each beep (longer fade)
          let envelope = 1;
          const fadeTime = 0.05; // 50ms fade in/out for smoother, more ambient sound
          const fadeFrames = fadeTime * sampleRate;
          
          if (i - beepStartFrame < fadeFrames) {
            // Fade in
            envelope = (i - beepStartFrame) / fadeFrames;
          } else if (beepEndFrame - i < fadeFrames) {
            // Fade out
            envelope = (beepEndFrame - i) / fadeFrames;
          }
          
          // Apply exponential curve for more natural sound
          envelope = Math.pow(envelope, 0.7);
          
          // Generate sine wave with slight harmonic for warmth
          const mainTone = Math.sin(2 * Math.PI * frequency * timeInBeep);
          const harmonic = 0.1 * Math.sin(2 * Math.PI * frequency * 2 * timeInBeep); // Subtle octave harmonic
          const sample = volume * envelope * (mainTone + harmonic);
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