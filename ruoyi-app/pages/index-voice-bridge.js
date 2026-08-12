  const TARGET_INPUT_RATE = 16000
  const OUTPUT_RATE = 24000

  export default {
    data() {
      return {
        lastSerial: -1,
        socket: null,
        captureContext: null,
        playbackContext: null,
        mediaStream: null,
        processor: null,
        mediaSource: null,
        muted: false,
        manualStop: false,
        nextPlayAt: 0,
        playingSources: [],
        assistantText: '',
        textTimer: null,
        playbackTimer: null,
        speakingSent: false,
        responding: false,
        connectionOptions: null,
        reconnectAttempts: 0,
        reconnectTimer: null,
        keepaliveTimer: null
      }
    },
    methods: {
      unlockAudio() {
        const context = this.ensurePlaybackContext()
        if (context && context.state === 'suspended') context.resume().catch(() => {})
      },
      onCommand(command) {
        if (!command || command.serial === this.lastSerial) return
        this.lastSerial = command.serial
        if (command.action === 'start') this.start(command)
        if (command.action === 'stop') this.stop(true)
        if (command.action === 'mute') this.setMuted(Boolean(command.muted))
      },
      emit(event) {
        if (this.$ownerInstance && event) {
          this.$ownerInstance.callMethod('onVoiceEvent', event)
        }
      },
      async start(options) {
        await this.stop(false)
        this.manualStop = false
        this.muted = false
        this.assistantText = ''
        this.speakingSent = false
        this.responding = false
        this.connectionOptions = {
          url: options.url,
          token: options.token || '',
          clientId: options.clientId || 'mobile'
        }
        this.reconnectAttempts = 0
        this.openSocket()
      },
      openSocket() {
        const options = this.connectionOptions
        if (this.manualStop || !options) return
        try {
          const socket = new WebSocket(options.url)
          this.socket = socket
          socket.onopen = () => {
            if (this.socket !== socket || this.manualStop) return
            socket.send(JSON.stringify({
              type: 'client.hello',
              token: options.token || '',
              client_id: options.clientId || 'mobile'
            }))
            this.startKeepalive(socket)
          }
          socket.onmessage = event => this.handleServerEvent(event.data)
          socket.onerror = () => {}
          socket.onclose = event => {
            if (this.socket !== socket) return
            this.socket = null
            this.stopKeepalive()
            this.stopCapture()
            this.clearPlayback()
            if (this.manualStop) {
              this.emit({ type: 'closed' })
            } else {
              this.scheduleReconnect(event.reason)
            }
          }
        } catch (error) {
          this.scheduleReconnect(error.message || String(error))
        }
      },
      scheduleReconnect(reason) {
        if (this.manualStop || !this.connectionOptions || this.reconnectTimer) return
        this.reconnectAttempts += 1
        const delay = Math.min(15000, 800 * Math.pow(2, Math.min(this.reconnectAttempts - 1, 5)))
        this.emit({
          type: 'reconnecting',
          attempt: this.reconnectAttempts,
          message: reason ? `正在恢复长期待命连接：${reason}` : '正在恢复长期待命连接'
        })
        this.reconnectTimer = setTimeout(() => {
          this.reconnectTimer = null
          this.openSocket()
        }, delay)
      },
      startKeepalive(socket) {
        this.stopKeepalive()
        this.keepaliveTimer = setInterval(() => {
          if (this.socket === socket && socket.readyState === WebSocket.OPEN) {
            try { socket.send(JSON.stringify({ type: 'ping', timestamp: Date.now() })) } catch (error) {}
          }
        }, 20000)
      },
      stopKeepalive() {
        if (this.keepaliveTimer) clearInterval(this.keepaliveTimer)
        this.keepaliveTimer = null
      },
      async stop(emitClosed) {
        this.manualStop = true
        if (this.reconnectTimer) clearTimeout(this.reconnectTimer)
        this.reconnectTimer = null
        this.stopKeepalive()
        this.stopCapture()
        this.clearPlayback()
        const socket = this.socket
        this.socket = null
        this.connectionOptions = null
        if (socket) {
          socket.onclose = null
          socket.onmessage = null
          socket.onerror = null
          try { socket.close(1000, 'client ended') } catch (error) {}
        }
        if (emitClosed) this.emit({ type: 'closed' })
      },
      async handleServerEvent(raw) {
        let event
        try { event = JSON.parse(raw) } catch (error) { return }
        const type = event.type || ''
        if (type === 'assistant.session.ready') {
          try {
            this.reconnectAttempts = 0
            await this.startCapture()
            this.emit({ type: 'ready', continuous: true, memoryEnabled: Boolean(event.memory_enabled) })
          } catch (error) {
            this.emit({ type: 'error', message: `麦克风不可用：${error.message || error}` })
            this.stop(false)
          }
          return
        }
        if (type === 'input_audio_buffer.speech_started') {
          if (this.responding && this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify({ type: 'response.cancel' }))
          }
          this.clearPlayback()
          this.speakingSent = false
          this.responding = false
          this.emit({ type: 'speech.started' })
          return
        }
        if (type === 'input_audio_buffer.speech_stopped') {
          this.emit({ type: 'speech.stopped' })
          return
        }
        if (type === 'conversation.item.input_audio_transcription.completed') {
          this.emit({ type: 'user.text', text: event.transcript || '', final: true })
          return
        }
        if (type === 'response.created') {
          this.assistantText = ''
          this.speakingSent = false
          this.responding = true
          this.emit({ type: 'assistant.thinking' })
          return
        }
        if (type === 'response.audio_transcript.delta' || type === 'response.text.delta') {
          this.assistantText += event.delta || ''
          this.scheduleTextUpdate()
          return
        }
        if (type === 'response.audio_transcript.done' || type === 'response.text.done') {
          this.assistantText = event.transcript || event.text || this.assistantText
          this.flushTextUpdate(true)
          return
        }
        if (type === 'response.audio.delta') {
          if (!this.speakingSent) {
            this.speakingSent = true
            this.emit({ type: 'assistant.speaking' })
          }
          if (!this.muted) this.playPcm(event.delta)
          return
        }
        if (type === 'response.done') {
          this.responding = false
          this.schedulePlaybackDone()
          return
        }
        if (type === 'assistant.session.rotating') {
          this.emit({ type: 'reconnecting', message: event.message || '正在续接长期待命会话' })
          if (this.socket) {
            try { this.socket.close(1000, 'rotate upstream session') } catch (error) {}
          }
          return
        }
        if (type === 'assistant.error' || type === 'error') {
          const message = event.message || (event.error && event.error.message) || '千问实时服务返回错误'
          const code = event.code || ''
          if (['unauthorized', 'missing_api_key', 'capacity', 'upstream_initialization_failed', 'upstream_access_denied'].includes(code)) {
            this.emit({ type: 'error', code, message })
            this.stop(false)
          } else {
            this.emit({ type: 'reconnecting', message: '云端短暂不可用，正在自动恢复' })
            if (this.socket) {
              try { this.socket.close(1012, 'retry upstream') } catch (error) {}
            }
          }
        }
      },
      async startCapture() {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
          throw new Error('当前 WebView 不支持实时麦克风，请升级系统 WebView')
        }
        this.stopCapture()
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            channelCount: 1,
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true
          },
          video: false
        })
        const AudioContextClass = window.AudioContext || window.webkitAudioContext
        if (!AudioContextClass) throw new Error('当前设备不支持 Web Audio')
        const context = new AudioContextClass()
        if (context.state === 'suspended') await context.resume()
        const source = context.createMediaStreamSource(stream)
        this.mediaStream = stream
        this.captureContext = context
        this.mediaSource = source

        let processor = await this.createCaptureWorklet(context)

        if (!processor) {
          processor = context.createScriptProcessor(2048, 1, 1)
          processor.onaudioprocess = audioEvent => {
            this.sendCaptureFrame(audioEvent.inputBuffer.getChannelData(0), context.sampleRate)
          }
        }
        source.connect(processor)
        processor.connect(context.destination)
        this.processor = processor
      },
      async createCaptureWorklet(context) {
        const WorkletNode = window.AudioWorkletNode
        if (!context.audioWorklet || !WorkletNode) return null

        const locationUrl = new URL(window.location.href)
        locationUrl.hash = ''
        locationUrl.search = ''
        const pageBase = new URL('.', locationUrl.href)
        const moduleUrls = Array.from(new Set([
          new URL('static/audio/pcm-capture-worklet.js', pageBase).href,
          new URL('/static/audio/pcm-capture-worklet.js', window.location.origin).href
        ]))
        let lastError = null
        let loaded = false

        for (const moduleUrl of moduleUrls) {
          try {
            await context.audioWorklet.addModule(moduleUrl)
            loaded = true
            break
          } catch (error) {
            lastError = error
          }
        }

        // 某些 HBuilderX H5 服务会为静态脚本返回不兼容的 MIME，改用 Blob 再加载一次。
        if (!loaded && typeof Blob !== 'undefined' && window.URL && window.URL.createObjectURL) {
          for (const moduleUrl of moduleUrls) {
            let blobUrl = ''
            try {
              const response = await fetch(moduleUrl, { cache: 'no-store' })
              if (!response.ok) throw new Error(`HTTP ${response.status}`)
              const source = await response.text()
              blobUrl = window.URL.createObjectURL(new Blob([source], { type: 'application/javascript' }))
              await context.audioWorklet.addModule(blobUrl)
              loaded = true
              break
            } catch (error) {
              lastError = error
            } finally {
              if (blobUrl) window.URL.revokeObjectURL(blobUrl)
            }
          }
        }

        if (!loaded) {
          console.warn('AudioWorklet 初始化失败，已回退兼容录音模式：', lastError)
          return null
        }

        try {
          const processor = new WorkletNode(context, 'tmall-pcm-capture', {
            numberOfInputs: 1,
            numberOfOutputs: 1,
            outputChannelCount: [1]
          })
          processor.port.onmessage = event => {
            this.sendCaptureFrame(new Float32Array(event.data), context.sampleRate)
          }
          return processor
        } catch (error) {
          console.warn('AudioWorklet 节点创建失败，已回退兼容录音模式：', error)
          return null
        }
      },
      sendCaptureFrame(input, inputRate) {
        if (this.muted || !this.socket || this.socket.readyState !== WebSocket.OPEN) return
        if (this.socket.bufferedAmount > 512 * 1024) return
        const pcm = this.downsampleToPcm16(input, inputRate, TARGET_INPUT_RATE)
        if (!pcm.length) return
        this.socket.send(JSON.stringify({
          type: 'input_audio_buffer.append',
          audio: this.bytesToBase64(new Uint8Array(pcm.buffer))
        }))
      },
      stopCapture() {
        if (this.processor) {
          this.processor.onaudioprocess = null
          if (this.processor.port) {
            this.processor.port.onmessage = null
            try { this.processor.port.close() } catch (error) {}
          }
          try { this.processor.disconnect() } catch (error) {}
        }
        if (this.mediaSource) {
          try { this.mediaSource.disconnect() } catch (error) {}
        }
        if (this.mediaStream) {
          this.mediaStream.getTracks().forEach(track => track.stop())
        }
        if (this.captureContext) {
          try { this.captureContext.close() } catch (error) {}
        }
        this.processor = null
        this.mediaSource = null
        this.mediaStream = null
        this.captureContext = null
      },
      setMuted(value) {
        this.muted = value
        if (value && this.socket && this.socket.readyState === WebSocket.OPEN) {
          this.socket.send(JSON.stringify({ type: 'input_audio_buffer.clear' }))
        }
      },
      downsampleToPcm16(input, inputRate, outputRate) {
        if (!input || !input.length || outputRate > inputRate) return new Int16Array(0)
        const ratio = inputRate / outputRate
        const outputLength = Math.floor(input.length / ratio)
        const output = new Int16Array(outputLength)
        for (let index = 0; index < outputLength; index += 1) {
          const start = Math.floor(index * ratio)
          const end = Math.max(start + 1, Math.floor((index + 1) * ratio))
          let total = 0
          let count = 0
          for (let cursor = start; cursor < end && cursor < input.length; cursor += 1) {
            total += input[cursor]
            count += 1
          }
          const sample = Math.max(-1, Math.min(1, total / Math.max(1, count)))
          output[index] = sample < 0 ? sample * 32768 : sample * 32767
        }
        return output
      },
      bytesToBase64(bytes) {
        let binary = ''
        const size = 8192
        for (let offset = 0; offset < bytes.length; offset += size) {
          binary += String.fromCharCode.apply(null, bytes.subarray(offset, offset + size))
        }
        return btoa(binary)
      },
      ensurePlaybackContext() {
        if (!this.playbackContext || this.playbackContext.state === 'closed') {
          const AudioContextClass = window.AudioContext || window.webkitAudioContext
          if (!AudioContextClass) return null
          this.playbackContext = new AudioContextClass()
          this.nextPlayAt = this.playbackContext.currentTime
        }
        return this.playbackContext
      },
      playPcm(base64Audio) {
        if (!base64Audio) return
        const context = this.ensurePlaybackContext()
        if (!context) return
        if (context.state === 'suspended') context.resume().catch(() => {})
        const binary = atob(base64Audio)
        const sampleCount = Math.floor(binary.length / 2)
        if (!sampleCount) return
        const buffer = context.createBuffer(1, sampleCount, OUTPUT_RATE)
        const channel = buffer.getChannelData(0)
        for (let index = 0; index < sampleCount; index += 1) {
          const low = binary.charCodeAt(index * 2)
          const high = binary.charCodeAt(index * 2 + 1)
          let sample = (high << 8) | low
          if (sample >= 0x8000) sample -= 0x10000
          channel[index] = sample / 32768
        }
        const source = context.createBufferSource()
        source.buffer = buffer
        source.connect(context.destination)
        const startAt = Math.max(context.currentTime + 0.025, this.nextPlayAt)
        this.nextPlayAt = startAt + buffer.duration
        this.playingSources.push(source)
        source.onended = () => {
          this.playingSources = this.playingSources.filter(item => item !== source)
        }
        source.start(startAt)
      },
      clearPlayback() {
        if (this.playbackTimer) clearTimeout(this.playbackTimer)
        this.playbackTimer = null
        this.playingSources.forEach(source => {
          try { source.stop() } catch (error) {}
        })
        this.playingSources = []
        if (this.playbackContext) this.nextPlayAt = this.playbackContext.currentTime
      },
      schedulePlaybackDone() {
        if (this.playbackTimer) clearTimeout(this.playbackTimer)
        const context = this.playbackContext
        const delay = context ? Math.max(80, (this.nextPlayAt - context.currentTime) * 1000 + 100) : 80
        this.playbackTimer = setTimeout(() => this.emit({ type: 'playback.done' }), delay)
      },
      scheduleTextUpdate() {
        if (this.textTimer) return
        this.textTimer = setTimeout(() => this.flushTextUpdate(false), 100)
      },
      flushTextUpdate(final = false) {
        if (this.textTimer) clearTimeout(this.textTimer)
        this.textTimer = null
        this.emit({ type: 'assistant.text', text: this.assistantText, final })
      }
    }
  }
