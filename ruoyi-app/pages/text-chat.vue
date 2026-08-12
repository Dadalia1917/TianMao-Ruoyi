<template>
  <view class="text-chat-shell">
    <view v-if="historyVisible" class="text-drawer-mask" @tap="historyVisible = false"></view>

    <view class="text-sidebar" :class="{ open: historyVisible }">
      <view class="text-brand-row">
        <button class="text-back" @tap="goBack">‹</button>
        <view class="text-brand-mark"><view></view></view>
        <view class="text-brand-copy">
          <text class="text-brand-name">天猫智家 · 文字对话</text>
          <text class="text-brand-sub">TEXT ASSISTANT</text>
        </view>
        <button class="text-sidebar-close" @tap="historyVisible = false">×</button>
      </view>

      <button class="text-new-button" @tap="newConversation">
        <text class="text-new-icon">＋</text>
        <text>新建对话</text>
      </button>
      <view class="text-history-heading">
        <text>本机记录</text><text class="text-history-count">{{ histories.length }}</text>
      </view>
      <scroll-view class="text-history-scroll" scroll-y>
        <view v-if="!histories.length" class="text-history-empty">还没有文字对话</view>
        <view
          v-for="item in histories"
          :key="item.id"
          class="text-history-item"
          :class="{ selected: currentConversation && currentConversation.id === item.id }"
          @tap="openHistory(item)"
        >
          <view class="text-history-main">
            <text class="text-history-title">{{ item.title }}</text>
            <text class="text-history-preview">{{ historyPreview(item) }}</text>
            <text class="text-history-meta">{{ modelLabel(item.model) }} · {{ formatRelativeTime(item.updatedAt) }}</text>
          </view>
          <button class="text-history-delete" @tap.stop="deleteHistory(item.id)">×</button>
        </view>
      </scroll-view>
      <view class="text-sidebar-note">文字记录保存在当前设备，并按登录账号隔离</view>
    </view>

    <view class="text-main">
      <view class="text-header">
        <button class="text-menu" @tap="historyVisible = true"><view></view><view></view><view></view></button>
        <view class="text-header-copy">
          <text class="text-header-title">文字对话</text>
          <text class="text-header-sub">深度思考已开启</text>
        </view>
        <picker class="model-picker" :range="models" range-key="label" :value="selectedModelIndex" @change="changeModel">
          <view class="model-picker-value">
            <view class="model-status-dot"></view>
            <view class="model-picker-copy">
              <text class="model-picker-name">{{ selectedModel.label }}</text>
              <text class="model-picker-hint">{{ selectedModel.description }}</text>
            </view>
            <text class="model-picker-arrow">⌄</text>
          </view>
        </picker>
      </view>

      <scroll-view class="text-message-scroll" scroll-y :scroll-top="scrollTop">
        <view class="text-message-content">
          <view v-if="!messages.length" class="text-welcome">
            <view class="text-welcome-orb"><view class="text-welcome-chat-icon"></view></view>
            <text class="text-welcome-title">想聊点什么？</text>
            <text class="text-welcome-sub">可以键盘输入，也可以直接对着麦克风说话</text>
            <view class="text-suggestions">
              <button class="text-suggestion" @tap="useSuggestion('帮我制定一份今天的工作计划')">
                <text class="text-suggestion-icon">✓</text><text>制定工作计划</text>
              </button>
              <button class="text-suggestion" @tap="useSuggestion('解释一下大模型 Agent 是怎么工作的')">
                <text class="text-suggestion-icon">✦</text><text>了解 Agent</text>
              </button>
              <button class="text-suggestion" @tap="useSuggestion('帮我润色一段中文文案')">
                <text class="text-suggestion-icon">Aa</text><text>润色文案</text>
              </button>
            </view>
          </view>

          <view v-for="message in messages" :key="message.id" class="text-message" :class="`text-${message.role}`">
            <view v-if="message.role === 'assistant'" class="text-ai-avatar"><view></view></view>
            <view class="text-message-body">
              <text class="text-message-role">{{ message.role === 'user' ? '你' : selectedModel.label }}</text>
              <view v-if="message.reasoning" class="reasoning-panel">
                <button class="reasoning-toggle" @tap="toggleReasoning(message)">
                  <view class="reasoning-icon"></view>
                  <text>思考过程</text><text class="reasoning-arrow">{{ message.showReasoning ? '⌃' : '⌄' }}</text>
                </button>
                <text v-if="message.showReasoning" class="reasoning-text" selectable>{{ message.reasoning }}</text>
              </view>
              <text v-if="message.content" class="text-message-value" selectable>{{ message.content }}</text>
              <view v-if="message.streaming && !message.content" class="text-thinking"><view></view><view></view><view></view></view>
              <view v-if="message.role === 'assistant' && message.content && !message.streaming" class="text-message-actions">
                <button class="text-copy" @tap="toggleSpeech(message.content, message.id)">{{ speakingMessageId === message.id ? '停止播报' : '语音播报' }}</button>
                <button class="text-copy" @tap="copyText(message.content)">复制</button>
              </view>
            </view>
          </view>
          <view class="text-scroll-spacer"></view>
        </view>
      </scroll-view>

      <view class="text-composer-wrap">
        <view class="text-composer">
          <button class="text-mic" :class="{ recording: dictating, disabled: generating }" @tap="toggleDictation">
            <image class="mic-icon-image" src="/static/images/microphone.svg" mode="aspectFit"></image>
          </button>
          <textarea
            id="text-chat-input"
            name="text-chat-input"
            v-model="inputText"
            class="text-input"
            :placeholder="dictating ? '正在聆听，请直接说话…' : '输入问题，或点麦克风直接说…'"
            :maxlength="12000"
            :auto-height="true"
            :disabled="generating || dictating"
            confirm-type="send"
            @confirm="sendMessage"
          />
          <button v-if="generating" class="text-send text-stop" aria-label="停止生成" @tap="cancelGeneration"><view></view></button>
          <button v-else class="text-send" :class="{ disabled: !canSend }" aria-label="发送" @tap="sendMessage"><view class="text-send-arrow"></view></button>
        </view>
        <text class="text-composer-note">{{ dictating ? '正在聆听；点麦克风结束后自动发送' : '支持语音提问和自动播报；AI 生成内容可能不准确。' }}</text>
      </view>
    </view>
  </view>
</template>

<script>
  import config from '@/config'
  import { getToken, removeToken } from '@/utils/auth'
  import storage from '@/utils/storage'
  import constant from '@/utils/constant'
  import {
    loadTextChatHistory,
    makeTextConversation,
    saveTextChatHistory,
    textTitle
  } from '@/utils/textChatHistory'

  const CLIENT_ID_KEY = 'Assistant-Client-Id'

  export default {
    data() {
      const owner = String(storage.get(constant.id) || storage.get(constant.name) || 'signed-in')
      const histories = loadTextChatHistory(owner)
      return {
        models: [
          { key: 'qwen3.8-max', label: 'Qwen3.8-Max', description: '旗舰深度推理' },
          { key: 'qwen3.7-plus', label: 'Qwen3.7-Plus', description: '均衡高性价比' },
          { key: 'qwen3.7-flash', label: 'Qwen3.7-Flash', description: '轻量快速响应' },
          { key: 'deepseek-v4-pro', label: 'DeepSeek-V4-Pro', description: '旗舰深度思考' },
          { key: 'deepseek-v4-flash', label: 'DeepSeek-V4-Flash', description: '快速深度思考' },
          { key: 'deepseek-r1', label: 'DeepSeek-R1', description: '经典深度推理' }
        ],
        selectedModelKey: 'qwen3.7-plus',
        historyOwner: owner,
        histories,
        currentConversation: makeTextConversation('qwen3.7-plus'),
        inputText: '',
        generating: false,
        socketTask: null,
        requestCompleted: false,
        historyVisible: false,
        scrollTop: 0,
        dictating: false,
        recognition: null,
        dictationBase: '',
        dictationFinal: '',
        dictationShouldSend: false,
        speakingMessageId: '',
        speechUtterance: null
      }
    },
    computed: {
      selectedModel() {
        return this.models.find(item => item.key === this.selectedModelKey) || this.models[1]
      },
      selectedModelIndex() {
        return Math.max(0, this.models.findIndex(item => item.key === this.selectedModelKey))
      },
      messages() {
        return this.currentConversation ? this.currentConversation.messages : []
      },
      canSend() {
        return !this.generating && Boolean(this.inputText.trim())
      }
    },
    onUnload() {
      this.stopDictation(true)
      this.stopSpeaking()
      this.cancelGeneration(true)
    },
    methods: {
      goBack() {
        this.cancelGeneration(true)
        const pages = getCurrentPages()
        if (pages.length > 1) uni.navigateBack()
        else uni.reLaunch({ url: '/pages/index' })
      },
      normalizeTextWebSocketUrl(value) {
        let url = String(value || '').trim().replace(/\/$/, '')
        url = url.replace(/^http:\/\//i, 'ws://').replace(/^https:\/\//i, 'wss://')
        url = url.replace(/\/ws\/v1\/(assistant|text-chat)(?:\?.*)?$/i, '')
        return `${url}/ws/v1/text-chat`
      },
      getClientId() {
        let clientId = uni.getStorageSync(CLIENT_ID_KEY)
        if (!clientId) {
          clientId = `text-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
          uni.setStorageSync(CLIENT_ID_KEY, clientId)
        }
        return clientId
      },
      newConversation() {
        this.cancelGeneration(true)
        this.stopDictation(true)
        this.stopSpeaking()
        this.currentConversation = makeTextConversation(this.selectedModelKey)
        this.inputText = ''
        this.historyVisible = false
      },
      openHistory(item) {
        this.cancelGeneration(true)
        this.currentConversation = JSON.parse(JSON.stringify(item))
        this.selectedModelKey = this.models.some(model => model.key === item.model) ? item.model : 'qwen3.7-plus'
        this.currentConversation.messages.forEach(message => { message.showReasoning = false })
        this.historyVisible = false
        this.scrollToBottom()
      },
      changeModel(event) {
        const model = this.models[Number(event.detail.value)] || this.models[1]
        this.selectedModelKey = model.key
        if (this.currentConversation) this.currentConversation.model = model.key
      },
      modelLabel(key) {
        const model = this.models.find(item => item.key === key)
        return model ? model.label : key
      },
      historyPreview(item) {
        const message = [...(item.messages || [])].reverse().find(entry => entry.content)
        return message ? message.content : '文字对话'
      },
      formatRelativeTime(timestamp) {
        const date = new Date(timestamp)
        const today = new Date()
        if (date.toDateString() === today.toDateString()) {
          return `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`
        }
        return `${date.getMonth() + 1}月${date.getDate()}日`
      },
      useSuggestion(value) {
        this.inputText = value
      },
      toggleDictation() {
        if (this.generating) return
        if (this.dictating) {
          if (this.recognition) this.recognition.stop()
          return
        }
        const Recognition = typeof window !== 'undefined'
          ? (window.SpeechRecognition || window.webkitSpeechRecognition)
          : null
        if (!Recognition) {
          uni.showToast({ title: '当前浏览器不支持语音输入，请使用 Chrome 或键盘输入', icon: 'none' })
          return
        }
        this.stopSpeaking()
        const recognition = new Recognition()
        this.recognition = recognition
        this.dictationBase = this.inputText.trim()
        this.dictationFinal = ''
        this.dictationShouldSend = true
        recognition.lang = 'zh-CN'
        recognition.continuous = false
        recognition.interimResults = true
        recognition.onstart = () => { this.dictating = true }
        recognition.onresult = event => {
          let interim = ''
          for (let index = event.resultIndex; index < event.results.length; index += 1) {
            const value = String(event.results[index][0].transcript || '')
            if (event.results[index].isFinal) this.dictationFinal += value
            else interim += value
          }
          const speechText = `${this.dictationFinal}${interim}`.trim()
          this.inputText = [this.dictationBase, speechText].filter(Boolean).join('，')
        }
        recognition.onerror = event => {
          this.dictationShouldSend = false
          if (event.error !== 'aborted') {
            uni.showToast({ title: event.error === 'not-allowed' ? '请允许浏览器使用麦克风' : '语音识别失败，请重试', icon: 'none' })
          }
        }
        recognition.onend = () => {
          const shouldSend = this.dictationShouldSend && Boolean(this.dictationFinal.trim())
          this.dictating = false
          this.recognition = null
          this.dictationShouldSend = false
          if (shouldSend && !this.generating) setTimeout(() => this.sendMessage(), 120)
        }
        try {
          recognition.start()
        } catch (error) {
          this.recognition = null
          this.dictating = false
          uni.showToast({ title: '无法启动麦克风', icon: 'none' })
        }
      },
      stopDictation(cancel = true) {
        if (!this.recognition) return
        if (cancel) this.dictationShouldSend = false
        const recognition = this.recognition
        this.recognition = null
        this.dictating = false
        try {
          if (cancel && recognition.abort) recognition.abort()
          else recognition.stop()
        } catch (error) {}
      },
      toggleSpeech(content, messageId) {
        if (this.speakingMessageId === messageId) {
          this.stopSpeaking()
          return
        }
        this.speakText(content, messageId)
      },
      speakText(content, messageId) {
        if (typeof window === 'undefined' || !window.speechSynthesis || typeof SpeechSynthesisUtterance === 'undefined') {
          uni.showToast({ title: '当前浏览器不支持语音播报', icon: 'none' })
          return
        }
        this.stopSpeaking()
        const plainText = String(content || '')
          .replace(/```[\s\S]*?```/g, '代码内容已省略。')
          .replace(/[#*_>`~]/g, '')
          .trim()
        if (!plainText) return
        const utterance = new SpeechSynthesisUtterance(plainText)
        utterance.lang = 'zh-CN'
        utterance.rate = 1
        utterance.pitch = 1
        utterance.onstart = () => { this.speakingMessageId = messageId }
        utterance.onend = () => {
          if (this.speechUtterance === utterance) {
            this.speakingMessageId = ''
            this.speechUtterance = null
          }
        }
        utterance.onerror = utterance.onend
        this.speechUtterance = utterance
        window.speechSynthesis.speak(utterance)
      },
      stopSpeaking() {
        if (typeof window !== 'undefined' && window.speechSynthesis) window.speechSynthesis.cancel()
        this.speakingMessageId = ''
        this.speechUtterance = null
      },
      sendMessage() {
        if (!this.canSend) return
        const content = this.inputText.trim()
        this.stopDictation(true)
        this.stopSpeaking()
        if (!this.currentConversation) this.currentConversation = makeTextConversation(this.selectedModelKey)
        const userMessage = {
          id: `text-message-${Date.now()}-user`,
          role: 'user',
          content,
          reasoning: '',
          createdAt: Date.now()
        }
        const assistantMessage = {
          id: `text-message-${Date.now()}-assistant`,
          role: 'assistant',
          content: '',
          reasoning: '',
          showReasoning: true,
          streaming: true,
          createdAt: Date.now()
        }
        this.currentConversation.model = this.selectedModelKey
        this.currentConversation.messages.push(userMessage, assistantMessage)
        this.currentConversation.title = textTitle(this.currentConversation.messages)
        this.currentConversation.updatedAt = Date.now()
        this.inputText = ''
        this.generating = true
        this.requestCompleted = false
        this.scrollToBottom()
        this.openTextSocket()
      },
      createTextSocket(url) {
        // #ifdef H5
        // H5 下 uni.connectSocket 可能被 Vue3 运行时包装为 Promise，原生
        // WebSocket 适配器可以稳定提供与 SocketTask 一致的事件接口。
        const nativeSocket = new window.WebSocket(url)
        return {
          onOpen(callback) {
            nativeSocket.addEventListener('open', () => callback())
          },
          onMessage(callback) {
            nativeSocket.addEventListener('message', event => callback({ data: event.data }))
          },
          onError(callback) {
            nativeSocket.addEventListener('error', () => callback({ errMsg: 'WebSocket 连接失败' }))
          },
          onClose(callback) {
            nativeSocket.addEventListener('close', event => callback({ code: event.code, reason: event.reason }))
          },
          send(options = {}) {
            try {
              if (nativeSocket.readyState !== window.WebSocket.OPEN) {
                throw new Error('WebSocket 尚未连接')
              }
              nativeSocket.send(options.data)
              if (typeof options.success === 'function') options.success()
            } catch (error) {
              if (typeof options.fail === 'function') options.fail({ errMsg: error.message })
            }
          },
          close(options = {}) {
            try {
              if (nativeSocket.readyState !== window.WebSocket.CLOSED) {
                nativeSocket.close(options.code || 1000, options.reason || '')
              }
              if (typeof options.success === 'function') options.success()
            } catch (error) {
              if (typeof options.fail === 'function') options.fail({ errMsg: error.message })
            }
          }
        }
        // #endif

        // #ifndef H5
        return uni.connectSocket({
          url,
          success: () => {},
          fail: error => this.failGeneration((error && error.errMsg) || '无法连接文字对话服务')
        })
        // #endif
      },
      closeTextSocket(reason) {
        const task = this.socketTask
        this.socketTask = null
        if (!task || typeof task.close !== 'function') return
        try {
          task.close({ code: 1000, reason })
        } catch (error) {}
      },
      openTextSocket() {
        const url = this.normalizeTextWebSocketUrl(config.assistant.baseUrl)
        let task = null
        try {
          task = this.createTextSocket(url)
        } catch (error) {
          this.failGeneration(error.message || '无法创建文字对话连接')
          return
        }
        const taskMethods = ['onOpen', 'onMessage', 'onError', 'onClose', 'send', 'close']
        if (!task || taskMethods.some(method => typeof task[method] !== 'function')) {
          if (task && typeof task.catch === 'function') task.catch(() => {})
          this.failGeneration('当前运行环境未返回有效的 WebSocket 任务，请重新加载页面')
          return
        }
        this.socketTask = task
        task.onOpen(() => {
          const sourceMessages = this.currentConversation.messages.filter(message => !message.streaming)
          task.send({
            data: JSON.stringify({
              type: 'text.chat.start',
              token: getToken() || '',
              client_id: this.getClientId(),
              model: this.selectedModelKey,
              messages: sourceMessages.slice(-30).map(message => ({
                role: message.role,
                content: message.content
              }))
            }),
            fail: error => this.failGeneration((error && error.errMsg) || '问题发送失败，请重试')
          })
        })
        task.onMessage(event => this.handleTextEvent(event.data))
        task.onError(error => this.failGeneration((error && error.errMsg) || '无法连接文字对话服务'))
        task.onClose(() => {
          if (this.socketTask === task) this.socketTask = null
          if (this.generating && !this.requestCompleted) this.failGeneration('连接意外断开，请重试')
        })
      },
      handleTextEvent(raw) {
        let event
        try { event = JSON.parse(raw) } catch (error) { return }
        const assistant = this.currentConversation.messages[this.currentConversation.messages.length - 1]
        if (!assistant || assistant.role !== 'assistant') return
        if (event.type === 'text.reasoning.delta') assistant.reasoning += event.delta || ''
        if (event.type === 'text.answer.delta') assistant.content += event.delta || ''
        if (event.type === 'text.reasoning.delta' || event.type === 'text.answer.delta') {
          this.scrollToBottom()
          return
        }
        if (event.type === 'text.done') {
          this.requestCompleted = true
          this.generating = false
          assistant.streaming = false
          this.persistConversation()
          this.closeTextSocket('completed')
          this.speakText(assistant.content, assistant.id)
          return
        }
        if (event.type === 'text.error') {
          if (event.code === 'unauthorized') {
            removeToken()
            setTimeout(() => uni.reLaunch({ url: '/pages/login?reason=expired' }), 400)
          }
          this.failGeneration(event.message || '模型调用失败')
        }
      },
      failGeneration(message) {
        if (!this.generating && this.requestCompleted) return
        const assistant = this.currentConversation && this.currentConversation.messages[this.currentConversation.messages.length - 1]
        if (assistant && assistant.role === 'assistant') {
          assistant.streaming = false
          if (!assistant.content) assistant.content = `请求失败：${message}`
        }
        this.generating = false
        this.requestCompleted = true
        this.persistConversation()
        this.closeTextSocket('failed')
      },
      cancelGeneration(silent = false) {
        if (!this.generating && !this.socketTask) return
        this.requestCompleted = true
        this.generating = false
        this.closeTextSocket('cancelled')
        const assistant = this.currentConversation && this.currentConversation.messages[this.currentConversation.messages.length - 1]
        if (assistant && assistant.streaming) {
          assistant.streaming = false
          if (!assistant.content && !silent) assistant.content = '已停止生成。'
        }
        if (!silent) this.persistConversation()
      },
      persistConversation() {
        if (!this.currentConversation || !this.currentConversation.messages.length) return
        this.currentConversation.title = textTitle(this.currentConversation.messages)
        this.currentConversation.updatedAt = Date.now()
        try {
          const rest = this.histories.filter(item => item.id !== this.currentConversation.id)
          this.histories = saveTextChatHistory([this.currentConversation, ...rest], this.historyOwner)
        } catch (error) {
          uni.showToast({ title: '本机记录保存失败', icon: 'none' })
        }
      },
      toggleReasoning(message) {
        message.showReasoning = !message.showReasoning
      },
      copyText(content) {
        uni.setClipboardData({ data: content })
      },
      deleteHistory(id) {
        uni.showModal({
          title: '删除这条文字对话？', content: '删除后无法恢复。', confirmColor: '#dd6277',
          success: result => {
            if (!result.confirm) return
            this.histories = saveTextChatHistory(this.histories.filter(item => item.id !== id), this.historyOwner)
            if (this.currentConversation && this.currentConversation.id === id) this.currentConversation = makeTextConversation(this.selectedModelKey)
          }
        })
      },
      scrollToBottom() {
        this.$nextTick(() => { this.scrollTop = Date.now() })
      }
    }
  }
</script>

<style lang="scss">
  @import './text-chat.scss';
</style>
