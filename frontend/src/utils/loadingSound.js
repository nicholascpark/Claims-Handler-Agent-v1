/**
 * Utility for generating an aesthetic AI "thinking" sound using Web Audio API
 * Creates a gentle, harmonic pulsing pattern that evokes AI cognitive processing
 */

export const generateLoadingSound = () => {
  return new Promise((resolve, reject) => {
    try {
      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      const sampleRate = audioContext.sampleRate;
      const totalDuration = 3.0; // 3 seconds for a complete thinking cycle
      const frameCount = sampleRate * totalDuration;
      
      const audioBuffer = audioContext.createBuffer(1, frameCount, sampleRate);
      const channelData = audioBuffer.getChannelData(0);
      
      // AI thinking sound parameters - harmonic and ambient
      const baseFrequency = 220; // Low A note - foundational thinking tone
      const harmonicFreq1 = 330; // Perfect fifth - adds intelligence
      const harmonicFreq2 = 440; // Octave - adds clarity
      const pulseBeatFrequency = 0.8; // Gentle pulsing like breathing/heartbeat
      const volume = 0.03; // Very subtle - thoughtful presence
      
      // Clear the entire buffer first
      for (let i = 0; i < frameCount; i++) {
        channelData[i] = 0;
      }
      
      // Generate the AI thinking pattern
      for (let i = 0; i < frameCount; i++) {
        const time = i / sampleRate;
        
        // Create a gentle breathing/pulsing envelope
        const breathingCycle = Math.sin(2 * Math.PI * pulseBeatFrequency * time);
        const pulseEnvelope = 0.3 + 0.7 * (breathingCycle * 0.5 + 0.5); // Ranges from 0.3 to 1.0
        
        // Create smooth fade-in and fade-out for the entire duration
        let globalEnvelope = 1;
        const fadeTime = 0.2; // 200ms fade
        const fadeFrames = fadeTime * sampleRate;
        
        if (i < fadeFrames) {
          // Fade in
          globalEnvelope = i / fadeFrames;
        } else if (i > frameCount - fadeFrames) {
          // Fade out
          globalEnvelope = (frameCount - i) / fadeFrames;
        }
        
        // Apply smooth curves for natural, organic feeling
        globalEnvelope = Math.pow(globalEnvelope, 0.6);
        pulseEnvelope = Math.pow(pulseEnvelope, 0.8);
        
        // Generate harmonic layers for AI intelligence feeling
        const baseTone = Math.sin(2 * Math.PI * baseFrequency * time);
        const harmonic1 = 0.4 * Math.sin(2 * Math.PI * harmonicFreq1 * time);
        const harmonic2 = 0.2 * Math.sin(2 * Math.PI * harmonicFreq2 * time);
        
        // Add subtle frequency modulation for "neural activity" feeling
        const neuralModulation = 0.05 * Math.sin(2 * Math.PI * 3.7 * time); // Slight warble
        const modulatedBase = Math.sin(2 * Math.PI * baseFrequency * time * (1 + neuralModulation));
        
        // Combine all elements
        const thinkingTone = (modulatedBase * 0.6 + harmonic1 + harmonic2);
        const finalSample = volume * globalEnvelope * pulseEnvelope * thinkingTone;
        
        channelData[i] = finalSample;
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
  // Always regenerate for now to use the new AI thinking sound
  cachedLoadingSound = await generateLoadingSound();
  return cachedLoadingSound;
};

export const clearLoadingSoundCache = () => {
  cachedLoadingSound = null;
}; 