class TmallPcmCaptureProcessor extends AudioWorkletProcessor {
  constructor() {
    super()
    this.chunkSize = 2048
    this.buffer = new Float32Array(this.chunkSize)
    this.offset = 0
  }

  process(inputs) {
    const input = inputs[0]
    const channel = input && input[0]
    if (!channel || !channel.length) return true

    let cursor = 0
    while (cursor < channel.length) {
      const count = Math.min(channel.length - cursor, this.chunkSize - this.offset)
      this.buffer.set(channel.subarray(cursor, cursor + count), this.offset)
      cursor += count
      this.offset += count
      if (this.offset === this.chunkSize) {
        const completed = this.buffer
        this.port.postMessage(completed.buffer, [completed.buffer])
        this.buffer = new Float32Array(this.chunkSize)
        this.offset = 0
      }
    }
    return true
  }
}

registerProcessor('tmall-pcm-capture', TmallPcmCaptureProcessor)
