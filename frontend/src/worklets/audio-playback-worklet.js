/**
 * Audio Playback Worklet (bundled)
 * Handles audio playback from base64 PCM16 data received via WebSocket
 */

class AudioPlaybackWorklet extends AudioWorkletProcessor {
  constructor() {
    super()

    this.outputSampleRate = sampleRate
    this.inputSampleRate = 24000
    this.rateInToOut = this.inputSampleRate / this.outputSampleRate

    this.inputCapacity = Math.floor(this.inputSampleRate * 3)
    this.inputBuffer = new Float32Array(this.inputCapacity)
    this.inRead = 0
    this.inWrite = 0
    this.inAvailable = 0

    this.minInputFrames = Math.floor(this.inputSampleRate * 0.15)
    this.maxInputFrames = Math.floor(this.inputSampleRate * 0.5)

    this.srcFrac = 0.0
    this.started = false

    this.port.onmessage = (event) => {
      const data = event.data
      if (data && data.audio) {
        const pcm16 = data.audio
        const len = pcm16.length
        for (let i = 0; i < len; i++) {
          const v = Math.max(-1, Math.min(1, pcm16[i] / 32768))
          this._writeInput(v)
        }

        if (this.inAvailable > this.maxInputFrames) {
          const drop = this.inAvailable - this.maxInputFrames
          this.inRead = (this.inRead + drop) % this.inputCapacity
          this.inAvailable -= drop
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

    if (!this.started) {
      if (this.inAvailable >= this.minInputFrames) {
        this.started = true
      } else {
        channelData.fill(0)
        return true
      }
    }

    const increment = this.rateInToOut

    for (let i = 0; i < framesToFill; i++) {
      if (this.inAvailable < 2) {
        channelData.fill(0, i)
        this.started = false
        break
      }

      const idx0 = this.inRead
      const idx1 = (this.inRead + 1) % this.inputCapacity
      const s0 = this._peek(idx0)
      const s1 = this._peek(idx1)
      const out = s0 + (s1 - s0) * this.srcFrac
      channelData[i] = out

      this.srcFrac += increment
      while (this.srcFrac >= 1.0) {
        this.srcFrac -= 1.0
        this._consumeInput(1)
      }
    }

    return true
  }
}

registerProcessor('audio-playback-worklet', AudioPlaybackWorklet)


