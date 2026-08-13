const browserLocation = typeof window !== 'undefined' ? window.location : null
const browserOrigin = browserLocation && /^https?:$/.test(browserLocation.protocol)
  ? browserLocation.origin
  : ''
const isH5DevelopmentServer = browserLocation && ['9090', '5173'].includes(browserLocation.port)
const useSameOriginGateway = Boolean(browserOrigin && !isH5DevelopmentServer)
const isNativeApp = process.env.UNI_PLATFORM === 'app'
// Android Studio 原生 WebView 容器使用 file:///android_asset/www/ 加载 H5 资源。
// file:/content: 页面没有可用的同源网关，需要显式走线上服务地址。
const isPackagedWebView = Boolean(browserLocation && ['file:', 'content:'].includes(browserLocation.protocol))
const productionGateway = 'http://120.55.64.225'

// H5 生产包由 Caddy 同源转发 Java REST 与 FastAPI WebSocket，避免把
// 127.0.0.1 烘焙进阿里云构建产物。HBuilderX 本机调试仍使用独立开发端口。
const accountApiBaseUrl = useSameOriginGateway
  ? browserOrigin
  : ((isNativeApp || isPackagedWebView) ? productionGateway : 'http://127.0.0.1:8080')
const assistantApiBaseUrl = useSameOriginGateway
  ? browserOrigin
  : ((isNativeApp || isPackagedWebView) ? productionGateway : 'http://127.0.0.1:8001')

// 应用全局配置
export default {
  // 若依账号服务；部署时统一改为生产 HTTPS 地址。
  baseUrl: accountApiBaseUrl,
  // AI 网关地址，仅由开发/部署人员配置，不在消费者界面中暴露。
  assistant: {
    baseUrl: assistantApiBaseUrl
  },
  // 应用信息
  appInfo: {
    // 应用名称
    name: "天猫智家语音助手",
    // 应用版本
    version: "1.1.0",
    // 应用logo
    logo: "/static/logo.png",
    // 官方网站
    site_url: "",
    // 政策协议
    agreements: [{
        title: "隐私政策",
        url: "/pages/common/agreement/index?type=privacy"
      },
      {
        title: "用户服务协议",
        url: "/pages/common/agreement/index?type=service"
      }
    ]
  }
}
