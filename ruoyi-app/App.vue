<script setup>
  import config from './config'
  import { useConfigStore, useUserStore } from '@/store'
  import { onLaunch, onShow } from '@dcloudio/uni-app'
  import { hasValidLocalSession } from '@/utils/auth'

  onLaunch(() => {
    initApp()
    if (guardSession()) refreshServerSession()
  })

  let lastDeepLink = ''
  let loginRedirecting = false
  let lastServerValidationAt = 0
  onShow(() => {
    if (!guardSession()) return
    refreshServerSession()
    // #ifdef APP-PLUS
    const args = plus.runtime.arguments || ''
    if (args && args !== lastDeepLink && args.indexOf('smartbutler://') === 0) {
      lastDeepLink = args
      uni.reLaunch({ url: '/pages/index?source=tmall' })
    }
    // #endif
  })

  // 初始化应用
  function initApp() {
    // 初始化应用配置
    initConfig()
  }

  function initConfig() {
    useConfigStore().setConfig(config)
  }

  function guardSession() {
    if (hasValidLocalSession(true)) {
      loginRedirecting = false
      return true
    }
    const pages = getCurrentPages()
    const route = pages.length ? `/${pages[pages.length - 1].route}` : ''
    if (!loginRedirecting && route !== '/pages/login' && route !== '/pages/register') {
      loginRedirecting = true
      uni.reLaunch({ url: '/pages/login' })
    }
    return false
  }

  function refreshServerSession() {
    const now = Date.now()
    if (now - lastServerValidationAt < 5 * 60 * 1000) return
    lastServerValidationAt = now
    // 打开应用即访问 /getInfo，使服务端的 30 天未活跃期同步滑动续期。
    useUserStore().getInfo().catch(() => {
      // 网络暂时不可用时保留本地身份；明确的 401 由 request.js 统一回到登录页。
    })
  }
</script>

<style lang="scss">
  @import '@/static/scss/index.scss'
</style>
