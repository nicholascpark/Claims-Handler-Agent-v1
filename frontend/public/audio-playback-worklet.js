/**
 * Audio Playback Worklet
 * Handles audio playback from base64 PCM16 data received via WebSocket
 */

class AudioPlaybackWorklet extends AudioWorkletProcessor {
  constructor() {
    super()
    this.buffer = []
    this.sampleRate = 24000

    this.port.onmessage = (event) => {
      if (event.data && event.data.audio) {
        // Received Int16Array audio data
        const audioData = event.data.audio
        
        // Convert int16 to float32 for Web Audio API
        const float32Data = new Float32Array(audioData.length)
        for (let i = 0; i < audioData.length; i++) {
          float32Data[i] = audioData[i] / (audioData[i] < 0 ? 0x8000 : 0x7FFF)
        }
        
        // Add to playback buffer
        this.buffer.push(...float32Data)
      }
    }
  }

  process(inputs, outputs, parameters) {
    const output = outputs[0]
    
    if (!output || !output[0]) {
      return true
    }

    const channelData = output[0]
    const framesToFill = channelData.length

    if (this.buffer.length >= framesToFill) {
      // We have enough data, fill the output
      for (let i = 0; i < framesToFill; i++) {
        channelData[i] = this.buffer.shift()
      }
    } else {
      // Not enough data, output silence
      channelData.fill(0)
    }

    return true
  }
}

registerProcessor('audio-playback-worklet', AudioPlaybackWorklet)
