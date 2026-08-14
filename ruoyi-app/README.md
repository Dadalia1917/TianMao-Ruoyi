# 天猫智家·千问智能语音助手客户端 / Tmall Smart Home Qwen Voice Client

**产品版本：v1.1.1 · 文档更新时间：2026 年 8 月 14 日 20:04:17（UTC+8）**

> 发布状态（2026 年 8 月 14 日 20:04:17）：语音识别优化与 AI-Agent 音乐放松场景已合并为 v1.1.1 正式 APK，完成签名并覆盖安装 T10S；包名 `com.jpx.tmallsmarthome`，`versionCode=111`，应用进程和 `MainActivity` 正常。

> 正式 APK：`apk/天猫智家语音助手-v1.1.1.apk`，大小 1,621,553 字节，SHA-256 `988B84AF6740FF0FD60907AC9B946412B6AD409E20EF6E3D6F4341A82650F458`；v1/v2 签名有效，本地、T10S 与云端归档哈希一致。

## v1.1.1 更新说明

- 当前家电控制方式保持为 T10S 天猫精灵内部文字指令：客户端收到已确认事件后调用 `GenieBridge.sendToGenie()`，原生层把 `data=<家居命令>`、`method=15` 通过 `ContentResolver.insert()` 提交到 `content://com.alibaba.ailabs.genie.assistant.provider/GenieApi`，由天猫精灵控制账号中已绑定的家电。该链路不经过、也不依赖 Home Assistant。
- 客户端只在原生调用未抛异常且返回 `accepted=true` 后，按原 `execution_id` 向 FastAPI 发送 `assistant.home_command.result / accepted_unverified`；拒绝或异常发送失败结果。`accepted_unverified` 表示“天猫精灵内部指令已提交”，不是客户端已读取到物理设备状态。
- Agent 支持舒适情境与身心状态分流；“我有点累了”“压力很大”“想放松”会建议休息、补水，并可选择播放舒缓轻音乐，确定性安全闸禁止把它们替换成开空调。只有用户二次确认后音乐命令才会到达原生桥。
- WebView 采集请求固定为 16 kHz、16-bit、单声道；构建脚本会把运行时加载的 `pcm-capture-worklet.js` 显式复制进 H5/App/Android 产物，避免因动态 URL 未被 Vite 发现而总是退回主线程录音。不兼容 AudioWorklet 的旧 WebView 仍会安全回退。
- 客户端会上报实际音轨采样率、AudioContext 采样率、处理器模式、累计音频帧与 WebSocket 背压丢帧；播报开始/结束状态同时提供给服务端做第二层回灌保护。
- 原生白名单现包含音乐播放器/音乐/歌曲及播放/来一首/放一首动作，最终命令为“播放一首舒缓的轻音乐”，继续通过 T10S 内置 `GenieApi / method=15` 提交，不依赖 Home Assistant。

## v1.1.0 更新说明

- 增加 Qwen3.5 Omni 智能家居指令识别及结构化事件处理。
- Android 客户端增加天猫精灵 ContentProvider 原生调用链路，不依赖运行时 ADB、root 或终端命令。
- 播放 Omni 回答时暂停麦克风上行，并在播放结束后等待扬声器尾音消失，修复 T10S 把助手自己的回答当成下一轮提问的问题。
- 语音主页建连后显示“等待唤醒”，环境谈话不会进入普通对话；必须先说“管家”，“天猫管家”等旧口令不再生效。单独呼喊固定回答“我在，有什么需要？”，也可在口令后直接附带问题。
- 中央聆听球支持状态化反馈：待命呼吸、唤醒/聆听放大与冰蓝波纹、思考流动、播报脉冲，并兼容系统减少动态效果设置。
- 支持语音结束对话：说“你可以退下了”“我不想跟你说话了”“结束对话”“先这样吧”“再见”等明确结束语，助手回应后自动关闭本轮并回到等待唤醒；下次需要重新说口令。
- Agent 的家居计划会先播报家庭状态、依据、推荐参数和拟执行动作；只有用户明确同意后客户端才接收执行事件。拒绝时取消并回到待命，含糊答复时要求用户明确说“执行”或“取消”；对话结束后还会拒绝延迟事件，避免误操作。
- 移除不可靠的 Provider 元数据预检，直接提交经过双重白名单校验的短设备指令；复合表达只保留“开灯”等实际控制部分。
- 加入前后端一致的通用家居设备/动作校验与高风险指令拦截。灯光、空调/新风、窗帘、影音、空气环境、清扫和智能插座共用同一条原生通道，保留房间、数值、档位和模式参数；普通语音、文字对话及长期记忆功能不变。
- 统一客户端、FastAPI、Android、Docker 镜像标签和安装包版本为 v1.1.0；Android `versionCode` 为 `110`。
- 修复 T10S 重启后悬浮入口消失：开机广播通过 1×1 透明引导 Activity 启动前台悬浮服务，完整助手页面保持关闭；悬浮球已更换为项目老鼠品牌图标，点击后才进入 APP。
- 最新正式 APK 已通过 v1/v2 签名校验并覆盖安装至 T10S，SHA-256 为 `661325B361B7E977F8F040A1B3B55CA056CE71189CB23E761FD17BD891CE576F`。

这是仓库的 uni-app 客户端，支持 H5 与 Android APK。完整架构和启动步骤请阅读仓库根目录 `README.md`。

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

登录后进入语音主页会自动建立连接，但初始状态是“等待唤醒”；H5 首次使用需允许麦克风权限。必须先说“管家”，单独呼喊会收到固定的“我在，有什么需要？”，口令后也可直接附带问题。明确说出退下/结束语后本轮关闭，下一轮必须重新唤醒。询问模型身份时会如实回答 Qwen3.5 Omni。
4. 真机调试时将 `config.js` 中两个地址改成电脑局域网 IP。

账号 API 和 AI 网关地址属于部署配置，不在消费者界面中展示或允许修改。发布 H5/APK 前由开发人员统一替换为生产 HTTPS/WSS 地址。

文字对话页在 H5 中使用浏览器的 Web Speech API：点麦克风说话，识别结束自动发送，模型回答完成后自动播报。建议使用最新版 Chrome/Edge；若浏览器不支持语音识别，页面会提示并保留键盘输入。后续打包 Android 工控屏时需将同一交互接到原生 ASR/TTS 能力，以避免不同 WebView 的实现差异。

不要在此目录放置百炼 API Key 或 Home Assistant Token。所有第三方密钥必须留在服务端。

页面不再设置 10 分钟通话上限。它会发送心跳，并在断网或服务端轮换上游千问会话时自动重连。H5 仍受浏览器后台节流限制；正式 Android 容器已通过原生前台服务维持 WebView、麦克风和 WebSocket，用户从右上角退出到天猫精灵主页或切到后台后仍可说“管家”唤醒。语音主页底部记录/开始/静音操作栏已移除。

“管家记忆”读取 FastAPI 的 `/api/v1/memories`，携带当前 RuoYi Token。长期记忆位于服务端 MySQL，而对话详情仍默认只保存在当前设备。

历史缓存为空、被截断或由旧版本双重编码时，客户端会自动兼容读取；无法恢复的损坏缓存会被清理，不再阻断页面初始化。
