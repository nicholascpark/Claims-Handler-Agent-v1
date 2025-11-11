/**
 * Audio Processor Worklet (bundled)
 * Processes microphone input and converts to PCM16 format for WebSocket transmission
 */

class AudioProcessorWorklet extends AudioWorkletProcessor {
  constructor() {
    super()
    this.bufferSize = 4096
    this.buffer = new Float32Array(this.bufferSize)
    this.bufferIndex = 0
  }

  process(inputs, outputs, parameters) {
    const input = inputs[0]
    if (!input || !input[0]) {
      return true
    }

    const channelData = input[0]
    for (let i = 0; i < channelData.length; i++) {
      this.buffer[this.bufferIndex++] = channelData[i]

      if (this.bufferIndex >= this.bufferSize) {
        // Convert float32 to int16 PCM
        const pcm16 = new Int16Array(this.bufferSize)
        for (let j = 0; j < this.bufferSize; j++) {
          const s = Math.max(-1, Math.min(1, this.buffer[j]))
          pcm16[j] = s < 0 ? s * 0x8000 : s * 0x7FFF
        }

        // Send to main thread
        this.port.postMessage(pcm16)

        // Reset buffer
        this.bufferIndex = 0
      }
    }

    return true
  }
}

registerProcessor('audio-processor-worklet', AudioProcessorWorklet)


