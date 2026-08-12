const TokenKey = 'App-Token'
const LastActiveKey = 'App-Session-Last-Active'
const MaxInactiveMs = 30 * 24 * 60 * 60 * 1000

export function getToken() {
  return uni.getStorageSync(TokenKey)
}

export function setToken(token) {
  uni.setStorageSync(TokenKey, token)
  markSessionActive()
  return token
}

export function removeToken() {
  uni.removeStorageSync(TokenKey)
  uni.removeStorageSync(LastActiveKey)
}

export function markSessionActive() {
  uni.setStorageSync(LastActiveKey, Date.now())
}

export function hasValidLocalSession(touch = false) {
  if (!getToken()) return false
  const lastActive = Number(uni.getStorageSync(LastActiveKey) || 0)
  if (lastActive && Date.now() - lastActive > MaxInactiveMs) {
    removeToken()
    return false
  }
  // 兼容升级前已登录的设备；首次读取时从现在开始计算 30 天未活跃期。
  if (touch || !lastActive) markSessionActive()
  return true
}
