const HISTORY_KEY = 'Assistant-Text-History-V1'
const MAX_CONVERSATIONS = 40
const MAX_MESSAGES = 80
const MAX_CONTENT_CHARS = 12000
const MAX_REASONING_CHARS = 16000

function storageKey(ownerKey) {
  const owner = String(ownerKey || 'unknown').replace(/[^a-zA-Z0-9_-]/g, '').slice(0, 64)
  return `${HISTORY_KEY}:${owner || 'unknown'}`
}

function normalizeMessage(message) {
  return {
    id: String((message && message.id) || `${Date.now()}-${Math.random()}`),
    role: message && message.role === 'assistant' ? 'assistant' : 'user',
    content: String((message && message.content) || '').slice(0, MAX_CONTENT_CHARS),
    reasoning: String((message && message.reasoning) || '').slice(0, MAX_REASONING_CHARS),
    createdAt: Number((message && message.createdAt) || Date.now())
  }
}

function normalizeConversation(conversation) {
  const messages = Array.isArray(conversation && conversation.messages)
    ? conversation.messages.filter(item => item && (item.content || item.reasoning)).slice(-MAX_MESSAGES).map(normalizeMessage)
    : []
  return {
    id: String((conversation && conversation.id) || `text-${Date.now()}`),
    title: String((conversation && conversation.title) || '新的文字对话').slice(0, 40),
    model: String((conversation && conversation.model) || 'qwen3.7-plus'),
    createdAt: Number((conversation && conversation.createdAt) || Date.now()),
    updatedAt: Number((conversation && conversation.updatedAt) || Date.now()),
    messages
  }
}

export function loadTextChatHistory(ownerKey) {
  const key = storageKey(ownerKey)
  try {
    const stored = uni.getStorageSync(key)
    if (stored === undefined || stored === null || stored === '') return []
    let parsed = stored
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
    uni.removeStorageSync(key)
    console.warn('文字对话缓存损坏，已自动重置')
    return []
  }
}

export function saveTextChatHistory(conversations, ownerKey) {
  const safe = (Array.isArray(conversations) ? conversations : [])
    .filter(item => item && Array.isArray(item.messages) && item.messages.length)
    .map(normalizeConversation)
    .sort((a, b) => b.updatedAt - a.updatedAt)
    .slice(0, MAX_CONVERSATIONS)
  uni.setStorageSync(storageKey(ownerKey), safe)
  return safe
}

export function makeTextConversation(model = 'qwen3.7-plus') {
  const now = Date.now()
  return {
    id: `text-${now}-${Math.random().toString(36).slice(2, 10)}`,
    title: '新的文字对话',
    model,
    createdAt: now,
    updatedAt: now,
    messages: []
  }
}

export function textTitle(messages) {
  const first = (messages || []).find(item => item.role === 'user' && item.content)
  if (!first) return '新的文字对话'
  const value = first.content.replace(/\s+/g, ' ').trim()
  return value.length > 22 ? `${value.slice(0, 22)}…` : value
}
