/**
 * Audio Playback Worklet
 * Handles audio playback from base64 PCM16 data received via WebSocket
 */

class AudioPlaybackWorklet extends AudioWorkletProcessor {
  constructor() {
    super()

    // Output sample rate of the current AudioContext
    this.outputSampleRate = sampleRate

    // Incoming PCM is 24 kHz from the server
    this.inputSampleRate = 24000
    this.rateInToOut = this.inputSampleRate / this.outputSampleRate

    // Input ring buffer sized in input frames (mono)
    // Keep up to ~3s of INPUT audio to absorb jitter
    this.inputCapacity = Math.floor(this.inputSampleRate * 3)
    this.inputBuffer = new Float32Array(this.inputCapacity)
    this.inRead = 0
    this.inWrite = 0
    this.inAvailable = 0

    // Prebuffer ~150ms of INPUT before starting playback to avoid underflows
    this.minInputFrames = Math.floor(this.inputSampleRate * 0.15)
    // Cap INPUT latency to ~500ms by dropping the oldest frames if backlog grows
    this.maxInputFrames = Math.floor(this.inputSampleRate * 0.5)

    // Fractional read position for resampling
    this.srcFrac = 0.0

    this.started = false

    this.port.onmessage = (event) => {
      const data = event.data
      if (data && data.audio) {
        // Int16Array → Float32 conversion (mono)
        const pcm16 = data.audio
        const len = pcm16.length
        for (let i = 0; i < len; i++) {
          const v = Math.max(-1, Math.min(1, pcm16[i] / 32768))
          this._writeInput(v)
        }

        // If buffer grows too large, drop the oldest to bound latency (in INPUT frames)
        if (this.inAvailable > this.maxInputFrames) {
          const drop = this.inAvailable - this.maxInputFrames
          this.inRead = (this.inRead + drop) % this.inputCapacity
          this.inAvailable -= drop
          // Reset fractional position to avoid drift after a large drop
          this.srcFrac = 0.0
        }
      }
    }
  }

  _writeInput(sample) {
    this.inputBuffer[this.inWrite] = sample
    this.inWrite = (this.inWrite + 1) % this.inputCapacity
    if (this.inAvailable < this.inputCapacity) {
      this.inAvailable++
    } else {
      // Overrun: drop oldest input frame
      this.inRead = (this.inRead + 1) % this.inputCapacity
    }
  }

  _peek(idx) {
    return this.inputBuffer[idx]
  }

  _consumeInput(frames) {
    this.inRead = (this.inRead + frames) % this.inputCapacity
    this.inAvailable -= frames
  }

  process(inputs, outputs, parameters) {
    const output = outputs[0]
    if (!output || !output[0]) return true

    const channelData = output[0]
    const framesToFill = channelData.length

    // Prime the jitter buffer before starting playback (in INPUT frames)
    if (!this.started) {
      if (this.inAvailable >= this.minInputFrames) {
        this.started = true
      } else {
        channelData.fill(0)
        return true
      }
    }

    const increment = this.rateInToOut // how many INPUT frames per OUTPUT frame

    for (let i = 0; i < framesToFill; i++) {
      // Need at least 2 input frames for linear interpolation
      if (this.inAvailable < 2) {
        // Underrun: output silence for the rest and re-enter prebuffering
        channelData.fill(0, i)
        this.started = false
        break
      }

      const idx0 = this.inRead
      const idx1 = (this.inRead + 1) % this.inputCapacity
      const s0 = this._peek(idx0)
      const s1 = this._peek(idx1)
      // Linear interpolation at fractional position
      const out = s0 + (s1 - s0) * this.srcFrac
      channelData[i] = out

      // Advance fractional input position by INPUT/OUTPUT ratio
      this.srcFrac += increment
      // Consume whole input frames when fractional crosses 1.0
      while (this.srcFrac >= 1.0) {
        this.srcFrac -= 1.0
        this._consumeInput(1)
      }
    }

    return true
  }
}

registerProcessor('audio-playback-worklet', AudioPlaybackWorklet)
