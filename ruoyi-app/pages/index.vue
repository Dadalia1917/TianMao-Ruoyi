<template>
  <view
    class="assistant-shell"
    :voice-command="voiceCommand"
    :change:voice-command="voiceBridge.onCommand"
    @click="voiceBridge.unlockAudio"
  >
    <view v-if="historyVisible" class="drawer-mask" @tap.stop="historyVisible = false"></view>

    <view class="history-sidebar" :class="{ 'history-open': historyVisible }" @tap.stop>
      <view class="sidebar-brand">
        <view class="brand-mark"><view class="brand-mark-core"></view></view>
        <view class="brand-copy">
          <text class="brand-cn">天猫智家</text>
          <text class="brand-en">TMALL SMART HOME</text>
        </view>
        <button class="sidebar-close" @tap="historyVisible = false" aria-label="关闭">×</button>
      </view>

      <button class="new-chat-button" @tap="newConversation">
        <text class="new-chat-plus">＋</text>
        <text>新建语音对话</text>
      </button>

      <view class="search-box">
        <view class="search-icon"></view>
        <input v-model.trim="searchQuery" class="search-input" placeholder="搜索本机对话" />
      </view>

      <button class="memory-nav text-chat-nav" @tap="openTextChatPage">
        <view class="memory-nav-icon text-chat-nav-icon"><view></view><view></view><view></view></view>
        <view class="memory-nav-copy">
          <text class="memory-nav-title">文字对话</text>
          <text class="memory-nav-hint">语音提问、深度思考与模型选择</text>
        </view>
        <text class="memory-nav-arrow">›</text>
      </button>

      <button class="memory-nav" @tap="openMemoryPage">
        <view class="memory-nav-icon"><view></view><view></view><view></view></view>
        <view class="memory-nav-copy">
          <text class="memory-nav-title">管家记忆</text>
          <text class="memory-nav-hint">查看天猫智家记住的内容</text>
        </view>
        <text class="memory-nav-arrow">›</text>
      </button>

      <view class="history-heading">
        <text>对话记录</text>
        <text class="history-count">{{ conversationHistory.length }}</text>
      </view>

      <scroll-view class="history-scroll" scroll-y>
        <view v-if="!groupedHistory.length" class="history-empty">
          <view class="empty-orb"></view>
          <text class="empty-title">还没有对话记录</text>
          <text class="empty-hint">每次语音对话会自动保存在本机</text>
        </view>
        <view v-for="group in groupedHistory" :key="group.label" class="history-group">
          <text class="group-label">{{ group.label }}</text>
          <view
            v-for="item in group.items"
            :key="item.id"
            class="history-item"
            :class="{ selected: selectedConversationId === item.id }"
            @tap="openConversation(item.id)"
          >
            <view class="history-item-main">
              <text class="history-title">{{ item.title }}</text>
              <text class="history-preview">{{ historyPreview(item) }}</text>
              <text class="history-time">{{ formatRelativeTime(item.updatedAt) }} · {{ formatTime(item.durationSeconds) }}</text>
            </view>
            <button class="delete-record" @tap.stop="deleteConversation(item.id)" aria-label="删除">×</button>
          </view>
        </view>
      </scroll-view>

      <view class="sidebar-footer">
        <view class="account-row">
          <view class="account-avatar">{{ accountInitial }}</view>
          <view class="account-copy"><text class="account-name">{{ accountName }}</text><text class="account-state">账号已登录</text></view>
          <button class="logout-action" @tap="logoutAccount">退出</button>
        </view>
        <button v-if="conversationHistory.length" class="footer-action danger-action" @tap="clearHistory"><text>清空记录</text></button>
        <text class="local-note">记录保存在当前设备，并按登录账号隔离</text>
      </view>
    </view>

    <view class="main-panel">
      <view class="ambient ambient-one"></view>
      <view class="ambient ambient-two"></view>

      <view class="app-header">
        <button class="header-icon menu-button" @tap.stop="historyVisible = true" aria-label="对话记录">
          <view class="menu-line"></view><view class="menu-line"></view><view class="menu-line"></view>
        </button>
        <view class="model-title">
          <text class="model-name">天猫智家</text>
          <text class="model-subtitle">Qwen3.5 Omni · 实时语音</text>
        </view>
      </view>

      <view v-if="memoryPageVisible" class="memory-page">
        <view class="detail-header memory-page-header">
          <button class="detail-back" @tap="closeMemoryPage">‹</button>
          <view class="detail-title-wrap">
            <text class="detail-title">管家记忆</text>
            <text class="detail-meta">新会话会自动使用当前账号的有效记忆</text>
          </view>
          <button v-if="memories.length" class="detail-delete" @tap="clearMemories">全部清除</button>
        </view>
        <scroll-view class="memory-scroll" scroll-y>
          <view class="memory-content">
            <view v-if="memoryLoading" class="memory-state"><view class="memory-loading-dot"></view><text>正在读取记忆…</text></view>
            <view v-else-if="memoryError" class="memory-state memory-error-state">
              <text class="memory-state-title">暂时无法读取记忆</text>
              <text class="memory-state-hint">{{ memoryError }}</text>
              <button class="memory-retry" @tap="loadMemories">重新加载</button>
            </view>
            <view v-else-if="!memories.length" class="memory-state">
              <view class="memory-empty-orb"></view>
              <text class="memory-state-title">还没有长期记忆</text>
              <text class="memory-state-hint">自然聊天即可。对话结束后，稳定的偏好和习惯会被整理到这里。</text>
            </view>
            <view v-else class="memory-list">
              <view v-for="item in memories" :key="item.memory_id" class="memory-card">
                <view class="memory-card-head">
                  <text class="memory-category">{{ memoryCategoryLabel(item.category) }}</text>
                  <button class="memory-delete" @tap="deleteMemory(item)">删除</button>
                </view>
                <text class="memory-value" selectable>{{ item.memory_value }}</text>
                <text class="memory-updated">更新于 {{ formatMemoryDate(item.update_time) }}</text>
              </view>
            </view>
            <view class="memory-privacy-note">
              <text>记忆按登录账号隔离，只用于改善后续对话。您可以随时删除单条或全部记忆。</text>
            </view>
          </view>
        </scroll-view>
      </view>

      <view v-else-if="selectedConversation" class="record-detail">
        <view class="detail-header">
          <button class="detail-back" @tap="closeConversation">‹</button>
          <view class="detail-title-wrap">
            <text class="detail-title">{{ selectedConversation.title }}</text>
            <text class="detail-meta">{{ formatFullDate(selectedConversation.createdAt) }} · {{ formatTime(selectedConversation.durationSeconds) }}</text>
          </view>
          <button class="detail-delete" @tap="deleteConversation(selectedConversation.id)">删除</button>
        </view>
        <scroll-view class="detail-scroll" scroll-y :scroll-top="detailScrollTop">
          <view class="detail-content">
            <view
              v-for="message in selectedConversation.messages"
              :key="message.id"
              class="detail-message"
              :class="`detail-${message.role}`"
            >
              <view v-if="message.role === 'assistant'" class="message-avatar"><view class="avatar-core"></view></view>
              <view class="message-body">
                <text class="message-role">{{ message.role === 'user' ? '你' : '天猫智家' }}</text>
                <text class="message-text" selectable>{{ message.content }}</text>
                <button class="copy-action" @tap="copyMessage(message.content)">复制</button>
              </view>
            </view>
            <view class="detail-end"><text>— 本次对话结束 —</text></view>
          </view>
        </scroll-view>
        <view class="detail-new-dock">
          <button class="detail-new-button" @tap="newConversation" aria-label="开始新的语音对话">
            <view class="detail-new-icon"><text>＋</text></view>
            <view class="detail-new-copy">
              <view class="detail-new-title-row">
                <text class="detail-new-title">开始新对话</text>
                <text class="detail-new-badge">实时语音</text>
              </view>
              <text class="detail-new-hint">返回助手主页并立即进入在线待命</text>
            </view>
            <view class="detail-new-arrow"></view>
          </button>
        </view>
      </view>

      <view v-else class="voice-page">
        <view class="session-meter availability-pill">
          <view class="availability-dot" :class="{ online: isActive }"></view>
          <text class="availability-title">{{ isActive ? '在线待命' : '天猫智家待命中' }}</text>
          <text class="meter-caption">{{ isActive ? '已陪伴 ' + formattedElapsed : '云端会话自动续接' }}</text>
        </view>

        <view class="assistant-stage">
          <view class="orb-rings" :class="orbClass"><view class="orb-ring ring-one"></view><view class="orb-ring ring-two"></view></view>
          <view class="orb-shadow" :class="orbClass"></view>
          <view class="assistant-orb" :class="orbClass">
            <view class="orb-glow orb-glow-one"></view>
            <view class="orb-glow orb-glow-two"></view>
          </view>
        </view>

        <view class="live-transcript" :class="{ empty: !visibleLiveMessages.length }">
          <view v-if="!visibleLiveMessages.length" class="welcome-copy">
            <text class="welcome-title">有什么我能帮您的吗？</text>
            <text class="welcome-hint">聊聊天、问问题，或者让天猫智家给您一些建议</text>
          </view>
          <view
            v-for="message in visibleLiveMessages"
            :key="message.id"
            class="live-message"
            :class="`live-${message.role}`"
          >
            <text class="live-role">{{ message.role === 'user' ? '你' : '管家' }}</text>
            <text class="live-text">{{ message.content }}</text>
            <view v-if="message.streaming" class="typing-dot"></view>
          </view>
        </view>

        <view class="status-area" @tap="startSession">
          <view class="voice-bars" :class="{ active: status === 'listening' || status === 'speaking' }">
            <view class="voice-bar bar-one"></view><view class="voice-bar bar-two"></view>
            <view class="voice-bar bar-three"></view><view class="voice-bar bar-four"></view>
          </view>
          <text class="status-title">{{ statusTitle }}</text>
          <text class="status-hint">{{ statusHint }}</text>
        </view>

        <view class="controls">
          <button class="control-button control-secondary" @tap.stop="historyVisible = true" aria-label="记录">
            <view class="history-control-icon"><view></view><view></view><view></view></view>
            <text class="control-label">记录</text>
          </button>
          <button
            class="control-button primary-control"
            :class="{ 'hangup-button': isActive }"
            @tap="isActive ? endSession() : startSession()"
            :aria-label="isActive ? '结束通话' : '开始对话'"
          >
            <view v-if="isActive" class="close-icon"></view>
            <view v-else class="start-wave"><view></view><view></view><view></view></view>
            <text class="control-label" :class="{ 'hangup-label': isActive }">{{ isActive ? '结束' : (status === 'error' ? '重试' : '开始') }}</text>
          </button>
          <button class="control-button control-secondary" @tap.stop="toggleMute" aria-label="麦克风">
            <view class="mic-icon" :class="{ muted: isMuted }"><image class="mic-icon-image" src="/static/images/microphone.svg" mode="aspectFit"></image></view>
            <text class="control-label">{{ isMuted ? '取消静音' : '静音' }}</text>
          </button>
        </view>
      </view>
    </view>

  </view>
</template>

<script>
  import config from '@/config'
  import { getToken, removeToken } from '@/utils/auth'
  import storage from '@/utils/storage'
  import constant from '@/utils/constant'
  import { useUserStore } from '@/store'
  import {
    loadAssistantHistory,
    makeConversationId,
    makeMessage,
    saveAssistantHistory,
    titleFromMessages
  } from '@/utils/assistantHistory'

  const CLIENT_ID_KEY = 'Assistant-Client-Id'

  export default {
    data() {
      const historyOwner = String(storage.get(constant.id) || storage.get(constant.name) || 'signed-in')
      return {
        status: 'idle',
        isMuted: false,
        elapsedSeconds: 0,
        latestUser: '',
        latestAssistant: '',
        errorMessage: '',
        voiceCommand: { serial: 0, action: 'idle' },
        timer: null,
        autoStartTimer: null,
        hasAutoStarted: false,
        historyVisible: false,
        searchQuery: '',
        serviceUrl: config.assistant.baseUrl,
        historyOwner,
        accountName: String(storage.get(constant.name) || '我的账号'),
        conversationHistory: loadAssistantHistory(historyOwner),
        currentConversation: null,
        selectedConversationId: '',
        detailScrollTop: 0,
        memoryPageVisible: false,
        memoryLoading: false,
        memoryError: '',
        memories: []
      }
    },
    computed: {
      formattedElapsed() { return this.formatTime(this.elapsedSeconds) },
      statusTitle() {
        const labels = {
          idle: '正在进入待命', connecting: '正在连接',
          listening: this.isMuted ? '麦克风已静音' : '我在听', thinking: '正在思考',
          speaking: '正在回复', error: '连接遇到问题', ended: '还想聊点什么？'
        }
        return labels[this.status] || '天猫智家'
      },
      statusHint() {
        if (this.status === 'idle') return '正在自动开启实时语音助手'
        if (this.status === 'ended') return '点击下方按钮可重新开始对话'
        if (this.status === 'connecting') return '正在恢复云端连接，对话会自动续接'
        if (this.status === 'error') return this.errorMessage || '请检查服务地址后重试'
        if (this.isMuted) return '点击右下角恢复麦克风'
        return '可以随时开口打断我'
      },
      orbClass() { return `orb-${this.status}${this.isMuted ? ' orb-muted' : ''}` },
      isActive() { return ['connecting', 'listening', 'thinking', 'speaking'].includes(this.status) },
      selectedConversation() {
        return this.conversationHistory.find(item => item.id === this.selectedConversationId) || null
      },
      accountInitial() { return this.accountName ? this.accountName.slice(0, 1).toUpperCase() : '我' },
      visibleLiveMessages() {
        return this.currentConversation ? this.currentConversation.messages.slice(-3) : []
      },
      groupedHistory() {
        const query = this.searchQuery.toLowerCase()
        const filtered = this.conversationHistory.filter(item => {
          if (!query) return true
          return item.title.toLowerCase().includes(query) || item.messages.some(message => message.content.toLowerCase().includes(query))
        })
        const startToday = new Date().setHours(0, 0, 0, 0)
        const groups = [
          { label: '今天', items: filtered.filter(item => item.updatedAt >= startToday) },
          { label: '过去 7 天', items: filtered.filter(item => item.updatedAt < startToday && item.updatedAt >= startToday - 6 * 86400000) },
          { label: '更早', items: filtered.filter(item => item.updatedAt < startToday - 6 * 86400000) }
        ]
        return groups.filter(group => group.items.length)
      }
    },
    onLoad(options) {
      // 旧开发版允许用户覆盖网关地址；正式消费者界面统一使用构建配置。
      uni.removeStorageSync('Assistant-Service-Url')
      this.scheduleAutoStart(options && options.source === 'tmall' ? 180 : 450)
    },
    onShow() {
      if (this.hasAutoStarted) this.scheduleAutoStart(280)
    },
    onHide() { this.cancelAutoStart() },
    beforeUnmount() {
      this.cancelAutoStart()
      this.endSession(true)
    },
    methods: {
      formatTime(seconds) {
        const safe = Math.max(0, Number(seconds) || 0)
        return `${Math.floor(safe / 60).toString().padStart(2, '0')}:${Math.floor(safe % 60).toString().padStart(2, '0')}`
      },
      formatRelativeTime(timestamp) {
        const date = new Date(timestamp)
        const today = new Date()
        if (date.toDateString() === today.toDateString()) return `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`
        return `${date.getMonth() + 1}月${date.getDate()}日`
      },
      formatFullDate(timestamp) {
        const date = new Date(timestamp)
        return `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日 ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`
      },
      historyPreview(item) {
        const message = item.messages[item.messages.length - 1]
        return message ? message.content : '语音对话'
      },
      normalizeWebSocketUrl(value) {
        let url = String(value || '').trim().replace(/\/$/, '')
        if (!/^https?:\/\//i.test(url) && !/^wss?:\/\//i.test(url)) return ''
        url = url.replace(/^http:\/\//i, 'ws://').replace(/^https:\/\//i, 'wss://')
        if (!/\/ws\/v1\/assistant(?:\?|$)/.test(url)) url += '/ws/v1/assistant'
        return url
      },
      normalizeHttpBase(value) {
        let url = String(value || '').trim().replace(/\/$/, '')
        url = url.replace(/^ws:\/\//i, 'http://').replace(/^wss:\/\//i, 'https://')
        return url.replace(/\/ws\/v1\/assistant(?:\?.*)?$/i, '')
      },
      assistantRequest(method, path) {
        return new Promise((resolve, reject) => {
          uni.request({
            url: `${this.normalizeHttpBase(this.serviceUrl)}${path}`,
            method,
            header: { Authorization: `Bearer ${getToken() || ''}` },
            success: response => {
              if (response.statusCode === 401) {
                removeToken()
                setTimeout(() => uni.reLaunch({ url: '/pages/login?reason=expired' }), 300)
                reject(new Error('登录状态已失效'))
                return
              }
              if (response.statusCode >= 200 && response.statusCode < 300) {
                resolve(response.data || {})
                return
              }
              if (method === 'GET' && path === '/api/v1/memories' && response.statusCode === 404) {
                reject(new Error('当前运行的是旧版语音服务，请重启 ruoyi-fastapi/main.py'))
                return
              }
              const detail = response.data && (response.data.detail || response.data.message)
              reject(new Error(detail || `服务返回 ${response.statusCode}`))
            },
            fail: error => reject(new Error(error.errMsg || '无法连接语音服务'))
          })
        })
      },
      getClientId() {
        let clientId = uni.getStorageSync(CLIENT_ID_KEY)
        if (!clientId) {
          clientId = `device-${Date.now()}-${Math.random().toString(36).slice(2, 12)}`
          uni.setStorageSync(CLIENT_ID_KEY, clientId)
        }
        return clientId
      },
      createCurrentConversation() {
        const now = Date.now()
        this.currentConversation = { id: makeConversationId(), title: '新的语音对话', createdAt: now, updatedAt: now, durationSeconds: 0, messages: [] }
      },
      scheduleAutoStart(delay = 350) {
        this.cancelAutoStart()
        this.autoStartTimer = setTimeout(() => {
          this.autoStartTimer = null
          if (this.isActive || this.selectedConversation || this.memoryPageVisible) return
          if (!['idle', 'ended'].includes(this.status)) return
          this.startSession()
        }, delay)
      },
      cancelAutoStart() {
        if (this.autoStartTimer) clearTimeout(this.autoStartTimer)
        this.autoStartTimer = null
      },
      requestMicrophonePermission() {
        return new Promise(resolve => {
          // #ifdef APP-PLUS
          if (typeof plus !== 'undefined' && plus.os && plus.os.name === 'Android') {
            plus.android.requestPermissions(
              ['android.permission.RECORD_AUDIO'],
              result => {
                const deniedAlways = Array.isArray(result.deniedAlways) ? result.deniedAlways : []
                const deniedPresent = Array.isArray(result.deniedPresent) ? result.deniedPresent : []
                if (deniedAlways.length) {
                  uni.showModal({
                    title: '需要麦克风权限',
                    content: '请在系统设置中允许天猫智家使用麦克风，才能进行实时语音对话。',
                    confirmText: '我知道了',
                    showCancel: false
                  })
                  resolve(false)
                  return
                }
                if (deniedPresent.length) {
                  uni.showToast({ title: '未获得麦克风权限', icon: 'none' })
                  resolve(false)
                  return
                }
                resolve(true)
              },
              () => {
                uni.showToast({ title: '无法申请麦克风权限', icon: 'none' })
                resolve(false)
              }
            )
            return
          }
          // #endif
          resolve(true)
        })
      },
      async startSession() {
        if (this.isActive || this.selectedConversation || this.memoryPageVisible) return
        if (!(await this.requestMicrophonePermission())) {
          this.status = 'ended'
          return
        }
        const wsUrl = this.normalizeWebSocketUrl(this.serviceUrl)
        if (!wsUrl) {
          this.errorMessage = '语音服务暂不可用，请联系客服'
          this.status = 'error'
          return
        }
        this.stopTimer()
        this.elapsedSeconds = 0
        this.latestUser = ''
        this.latestAssistant = ''
        this.errorMessage = ''
        this.isMuted = false
        this.status = 'connecting'
        this.hasAutoStarted = true
        this.createCurrentConversation()
        this.voiceCommand = { serial: this.voiceCommand.serial + 1, action: 'start', url: wsUrl, token: getToken() || '', clientId: this.getClientId() }
      },
      endSession(silent = false) {
        const shouldSignal = this.isActive || this.status === 'error'
        this.stopTimer()
        if (shouldSignal) this.voiceCommand = { serial: this.voiceCommand.serial + 1, action: 'stop' }
        this.finalizeCurrentConversation()
        if (!silent) {
          this.status = 'ended'
          this.isMuted = false
        }
      },
      newConversation() {
        if (this.isActive) this.endSession(true)
        this.selectedConversationId = ''
        this.memoryPageVisible = false
        this.currentConversation = null
        this.latestUser = ''
        this.latestAssistant = ''
        this.status = 'idle'
        this.historyVisible = false
        this.startSession()
      },
      appendUserMessage(content) {
        const text = String(content || '').trim()
        if (!text) return
        if (!this.currentConversation) this.createCurrentConversation()
        const last = this.currentConversation.messages[this.currentConversation.messages.length - 1]
        if (last && last.role === 'user' && last.content === text) return
        this.currentConversation.messages.push(makeMessage('user', text))
        this.currentConversation.title = titleFromMessages(this.currentConversation.messages)
        this.currentConversation.updatedAt = Date.now()
        this.latestUser = text
        this.persistCurrentConversation()
      },
      updateAssistantMessage(content, final = false) {
        const text = String(content || '').trim()
        if (!text) return
        if (!this.currentConversation) this.createCurrentConversation()
        const messages = this.currentConversation.messages
        const last = messages[messages.length - 1]
        if (last && last.role === 'assistant' && last.streaming) {
          last.content = text
          last.streaming = !final
        } else if (!(last && last.role === 'assistant' && last.content === text)) {
          messages.push(makeMessage('assistant', text, !final))
        }
        this.currentConversation.updatedAt = Date.now()
        this.latestAssistant = text
        if (final) this.persistCurrentConversation()
      },
      finalizeCurrentConversation() {
        if (!this.currentConversation) return
        this.currentConversation.durationSeconds = this.elapsedSeconds
        this.currentConversation.messages.forEach(message => { message.streaming = false })
        this.persistCurrentConversation()
      },
      persistCurrentConversation() {
        const current = this.currentConversation
        if (!current || !current.messages.length) return
        current.durationSeconds = this.elapsedSeconds
        current.title = titleFromMessages(current.messages)
        const rest = this.conversationHistory.filter(item => item.id !== current.id)
        this.conversationHistory = saveAssistantHistory([current, ...rest], this.historyOwner)
      },
      openConversation(id) {
        if (this.isActive) this.endSession()
        this.memoryPageVisible = false
        this.selectedConversationId = id
        this.historyVisible = false
        this.detailScrollTop = Date.now()
      },
      closeConversation() { this.selectedConversationId = '' },
      openTextChatPage() {
        if (this.isActive) this.endSession(true)
        this.historyVisible = false
        uni.navigateTo({ url: '/pages/text-chat' })
      },
      async openMemoryPage() {
        if (this.isActive) this.endSession(true)
        this.selectedConversationId = ''
        this.memoryPageVisible = true
        this.historyVisible = false
        await this.loadMemories()
      },
      closeMemoryPage() { this.memoryPageVisible = false },
      async loadMemories() {
        this.memoryLoading = true
        this.memoryError = ''
        try {
          const payload = await this.assistantRequest('GET', '/api/v1/memories')
          this.memories = Array.isArray(payload.items) ? payload.items : []
        } catch (error) {
          this.memoryError = error.message || '读取失败'
        } finally {
          this.memoryLoading = false
        }
      },
      memoryCategoryLabel(category) {
        return ({ preference: '偏好', profile: '个人资料', routine: '习惯', relationship: '重要关系', goal: '长期目标', other: '其他' })[category] || '其他'
      },
      formatMemoryDate(value) {
        if (!value) return '刚刚'
        const date = new Date(value)
        if (Number.isNaN(date.getTime())) return '最近'
        return `${date.getMonth() + 1}月${date.getDate()}日`
      },
      deleteMemory(item) {
        uni.showModal({
          title: '删除这条记忆？', content: item.memory_value, confirmColor: '#e14f66',
          success: async result => {
            if (!result.confirm) return
            try {
              await this.assistantRequest('DELETE', `/api/v1/memories/${item.memory_id}`)
              this.memories = this.memories.filter(memory => memory.memory_id !== item.memory_id)
            } catch (error) {
              uni.showToast({ title: error.message || '删除失败', icon: 'none' })
            }
          }
        })
      },
      clearMemories() {
        uni.showModal({
          title: '清除全部管家记忆？', content: '清除后，后续对话将不再使用这些内容。', confirmColor: '#e14f66',
          success: async result => {
            if (!result.confirm) return
            try {
              await this.assistantRequest('DELETE', '/api/v1/memories')
              this.memories = []
            } catch (error) {
              uni.showToast({ title: error.message || '清除失败', icon: 'none' })
            }
          }
        })
      },
      deleteConversation(id) {
        uni.showModal({
          title: '删除这条对话？', content: '删除后无法恢复。', confirmColor: '#e14f66',
          success: result => {
            if (!result.confirm) return
            this.conversationHistory = saveAssistantHistory(this.conversationHistory.filter(item => item.id !== id), this.historyOwner)
            if (this.selectedConversationId === id) this.selectedConversationId = ''
            if (this.currentConversation && this.currentConversation.id === id) this.currentConversation = null
          }
        })
      },
      clearHistory() {
        uni.showModal({
          title: '清空全部记录？', content: '当前设备上的对话记录将全部删除，且无法恢复。', confirmColor: '#e14f66',
          success: result => {
            if (!result.confirm) return
            this.conversationHistory = saveAssistantHistory([], this.historyOwner)
            this.selectedConversationId = ''
            this.currentConversation = null
          }
        })
      },
      copyMessage(content) { uni.setClipboardData({ data: content }) },
      logoutAccount() {
        uni.showModal({
          title: '退出当前账号？', content: '本机对话记录会保留，下次登录同一账号仍可查看。', confirmColor: '#d65e71',
          success: async result => {
            if (!result.confirm) return
            try { await useUserStore().logOut() } catch (error) { removeToken(); storage.clean() }
            uni.reLaunch({ url: '/pages/login' })
          }
        })
      },
      toggleMute() {
        if (!this.isActive || this.status === 'connecting') {
          uni.showToast({ title: '请先开始对话', icon: 'none' })
          return
        }
        this.isMuted = !this.isMuted
        this.voiceCommand = { serial: this.voiceCommand.serial + 1, action: 'mute', muted: this.isMuted }
        if (!this.isMuted) this.status = 'listening'
      },
      startTimer() {
        this.stopTimer()
        this.timer = setInterval(() => {
          this.elapsedSeconds += 1
        }, 1000)
      },
      stopTimer() { if (this.timer) clearInterval(this.timer); this.timer = null },
      onVoiceEvent(event) {
        if (!event || !event.type) return
        switch (event.type) {
          case 'ready': this.status = 'listening'; this.startTimer(); break
          case 'reconnecting': this.status = 'connecting'; this.errorMessage = event.message || ''; break
          case 'speech.started': this.status = 'listening'; break
          case 'speech.stopped':
          case 'assistant.thinking': this.status = 'thinking'; break
          case 'assistant.speaking': this.status = 'speaking'; break
          case 'relay.started': this.status = 'speaking'; break
          case 'agent.planning': this.status = 'thinking'; break
          case 'agent.notice':
            if (this.isActive) this.status = 'listening'
            uni.showToast({ title: event.message || '该操作暂未执行', icon: 'none', duration: 3200 })
            break
          case 'home.command.started': this.status = 'thinking'; break
          case 'home.command.accepted': this.status = 'speaking'; break
          case 'home.command.failed':
            if (this.isActive) this.status = 'listening'
            uni.showToast({ title: event.message || '家居指令提交失败', icon: 'none', duration: 3200 })
            break
          case 'playback.done': if (this.isActive) this.status = 'listening'; break
          case 'user.text': this.appendUserMessage(event.text); break
          case 'assistant.text': this.updateAssistantMessage(event.text, Boolean(event.final)); break
          case 'error':
            this.stopTimer()
            this.status = 'error'
            this.errorMessage = event.message || '实时语音服务连接失败'
            this.finalizeCurrentConversation()
            if (event.code === 'unauthorized') {
              removeToken()
              setTimeout(() => uni.reLaunch({ url: '/pages/login?reason=expired' }), 500)
            }
            break
          case 'closed': if (this.isActive) { this.stopTimer(); this.status = 'ended'; this.finalizeCurrentConversation() }; break
        }
      }
    }
  }
</script>

<script module="voiceBridge" lang="renderjs" src="./index-voice-bridge.js"></script>


<style lang="scss" scoped>
  @import './index-shell.scss';
</style>
