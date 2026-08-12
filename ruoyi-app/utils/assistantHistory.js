const HISTORY_KEY = 'Assistant-Conversation-History-V1'
const MAX_CONVERSATIONS = 60
const MAX_MESSAGES = 120
const MAX_MESSAGE_CHARS = 4000

function storageKey(ownerKey) {
  const owner = String(ownerKey || 'unknown').replace(/[^a-zA-Z0-9_-]/g, '').slice(0, 64)
  return `${HISTORY_KEY}:${owner || 'unknown'}`
}

function normalizeMessage(message) {
  const role = message && message.role === 'assistant' ? 'assistant' : 'user'
  return {
    id: String((message && message.id) || `${Date.now()}-${Math.random()}`),
    role,
    content: String((message && message.content) || '').slice(0, MAX_MESSAGE_CHARS),
    createdAt: Number((message && message.createdAt) || Date.now())
  }
}

function normalizeConversation(conversation) {
  const messages = Array.isArray(conversation && conversation.messages)
    ? conversation.messages.filter(item => item && item.content).slice(-MAX_MESSAGES).map(normalizeMessage)
    : []
  return {
    id: String((conversation && conversation.id) || `${Date.now()}`),
    title: String((conversation && conversation.title) || '新的语音对话').slice(0, 32),
    createdAt: Number((conversation && conversation.createdAt) || Date.now()),
    updatedAt: Number((conversation && conversation.updatedAt) || Date.now()),
    durationSeconds: Math.max(0, Number((conversation && conversation.durationSeconds) || 0)),
    messages
  }
}

export function loadAssistantHistory(ownerKey) {
  const key = storageKey(ownerKey)
  try {
    const stored = uni.getStorageSync(key)
    if (stored === undefined || stored === null || stored === '') return []
    let parsed = stored
    // H5、App WebView 以及旧版本可能分别返回对象、JSON 字符串或双重编码字符串。
    for (let depth = 0; depth < 2 && typeof parsed === 'string'; depth += 1) {
      const text = parsed.trim()
      if (!text) return []
      parsed = JSON.parse(text)
    }
    if (!Array.isArray(parsed)) {
      uni.removeStorageSync(key)
      return []
    }
    return parsed.map(normalizeConversation).sort((a, b) => b.updatedAt - a.updatedAt)
  } catch (error) {
    // 截断或损坏的本地 JSON 无法恢复，清理后让页面正常进入空历史状态。
    uni.removeStorageSync(key)
    console.warn('语音记录缓存损坏，已自动重置')
    return []
  }
}

export function saveAssistantHistory(conversations, ownerKey) {
  const safe = (Array.isArray(conversations) ? conversations : [])
    .filter(item => item && Array.isArray(item.messages) && item.messages.length)
    .map(normalizeConversation)
    .sort((a, b) => b.updatedAt - a.updatedAt)
    .slice(0, MAX_CONVERSATIONS)
  try {
    uni.setStorageSync(storageKey(ownerKey), safe)
  } catch (error) {
    console.warn('保存语音记录失败', error)
  }
  return safe
}

export function makeConversationId() {
  return `voice-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

export function makeMessage(role, content, streaming = false) {
  return {
    id: `message-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    role,
    content: String(content || '').slice(0, MAX_MESSAGE_CHARS),
    createdAt: Date.now(),
    streaming
  }
}

export function titleFromMessages(messages) {
  const firstUser = (messages || []).find(item => item.role === 'user' && item.content)
  if (!firstUser) return '新的语音对话'
  const text = firstUser.content.replace(/\s+/g, ' ').trim()
  return text.length > 18 ? `${text.slice(0, 18)}…` : text
}
