# 天猫智家·千问智能语音助手客户端 / Tmall Smart Home Qwen Voice Client

**产品版本：v1.0.0 · 文档日期：2026 年 8 月 11 日**

这是仓库的 uni-app 客户端，支持 H5 与后续 Android APK。完整架构和启动步骤请阅读仓库根目录 `README.md`。

This directory contains the uni-app H5/Android client. See the repository root `README.md` for the complete architecture and setup guide.

## 页面

- `pages/login.vue`：账号密码登录，登录状态连续 30 天未活跃后过期。
- `pages/register.vue`：账号注册。
- `pages/index.vue`：进入页面自动开启 Qwen 实时语音，并提供自动重连、流式字幕、历史详情、管家记忆和账号操作。
- `pages/index-voice-bridge.js`：独立 renderjs 音频桥，负责 H5/App WebView 的录音、WebSocket 和 PCM 播放；外链形式用于兼容 Vite 热更新。
- `pages/text-chat.vue`：六模型文字对话、麦克风语音输入、思考过程、自动语音播报和记录回看；不提供图片附件。
- `pages/text-chat.scss`：文字对话在手机、平板和工控横屏上的响应式样式。
- `pages/index-shell.scss`：手机、平板、中控和 H5 横屏响应式样式。
- `utils/assistantHistory.js`：按 RuoYi 用户 ID 隔离的本地历史记录。
- `utils/textChatHistory.js`：按账号隔离的本地文字对话记录。
- `utils/auth.js`：本地 30 天未活跃会话保护。
- `static/audio/pcm-capture-worklet.js`：H5 低延迟麦克风采集；旧 WebView 自动回退兼容模式。

## HBuilderX

1. 在 HBuilderX 中直接打开本目录。
2. 运行到浏览器（H5）。
3. 默认账号 API 为 `http://127.0.0.1:8080`，语音 API 为 `http://127.0.0.1:8001`。

登录后进入语音主页会自动执行“开始”流程；H5 首次使用需允许麦克风权限。单独说“天猫管家”会收到固定的“姥爷，我在”唤醒回应；询问模型身份时会如实回答 Qwen3.5 Omni。
4. 真机调试时将 `config.js` 中两个地址改成电脑局域网 IP。

账号 API 和 AI 网关地址属于部署配置，不在消费者界面中展示或允许修改。发布 H5/APK 前由开发人员统一替换为生产 HTTPS/WSS 地址。

文字对话页在 H5 中使用浏览器的 Web Speech API：点麦克风说话，识别结束自动发送，模型回答完成后自动播报。建议使用最新版 Chrome/Edge；若浏览器不支持语音识别，页面会提示并保留键盘输入。后续打包 Android 工控屏时需将同一交互接到原生 ASR/TTS 能力，以避免不同 WebView 的实现差异。

不要在此目录放置百炼 API Key 或 Home Assistant Token。所有第三方密钥必须留在服务端。

页面不再设置 10 分钟通话上限。它会发送心跳，并在断网或服务端轮换上游千问会话时自动重连。H5 受浏览器后台节流限制；真正的 Android 锁屏/后台常驻需在打包阶段增加原生前台服务，不能只依赖 WebView。

“管家记忆”读取 FastAPI 的 `/api/v1/memories`，携带当前 RuoYi Token。长期记忆位于服务端 MySQL，而对话详情仍默认只保存在当前设备。

历史缓存为空、被截断或由旧版本双重编码时，客户端会自动兼容读取；无法恢复的损坏缓存会被清理，不再阻断页面初始化。
