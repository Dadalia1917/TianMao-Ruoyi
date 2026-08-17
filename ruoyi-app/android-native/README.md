# 天猫智家 Android 原生容器

**产品版本：v1.1.2 · 文档更新时间：2026.08.17（UTC+8）**

该工程把 `ruoyi-app` 的 H5 产物装入 Android WebView，并为天猫精灵智慧屏 T10S 提供麦克风、开机悬浮入口和本机智能家居指令桥接。

## T10S 开机悬浮入口

T10S 固件会静默忽略第三方应用在开机广播中直接发出的前台服务启动请求。因此当前链路为：

1. `OverlayBootReceiver` 接收 `BOOT_COMPLETED`、快速启动或应用覆盖安装广播。
2. Receiver 启动 1×1、透明、不进入最近任务的 `OverlayBootstrapActivity`。
3. Bootstrap Activity 在正常 Activity 上下文中启动 `KeepAliveService`，约 300ms 内自动退出并返回天猫精灵原界面。
4. `KeepAliveService` 以前台服务形式持有右上角老鼠品牌图标悬浮球；冷启动后用户首次点击悬浮球打开 `MainActivity`。
5. 助手首次启动后，原生容器在返回天猫精灵主页或切换到后台时继续维持 WebView、麦克风和 WebSocket；悬浮球与前台页面都可接收“管家”唤醒。右上角退出按钮只回到天猫精灵主页，不杀死常驻运行时。

2026 年 8 月 13 日已完成真实重启验证：引导 Activity 启动服务后返回 `com.alibaba.genie.panel`，完整助手 UI 未自动打开；悬浮球持续可见，点击后可恢复 APP。2026.08.17（UTC+8）已把 Agent 自然确认、多方案放松、多动作保序执行和远场采集优化合并为 v1.1.2，覆盖安装到 `192.168.3.234:5555` 后确认 `versionCode=112`、`MainActivity` 和进程正常。正式 APK 大小 1,622,293 字节，SHA-256 为 `6BC2E4ADBC4422F6D3783E926F29FF3A07F2C5499B3683EF6010F3ECDC09E254`，并已通过 v1/v2 签名校验。

## T10S 家居指令链路

1. WebView 在 `client.hello` 中声明 `capabilities.genie_provider=true`。
2. FastAPI 从 Qwen 最终用户转写生成低风险家居计划，先播报家庭状态、证据、推荐参数和拟执行动作；只有用户明确同意后才下发 `assistant.home_command.pending` 结构化事件。
3. `index-voice-bridge.js` 读取服务端有序 `commands` 数组并逐条调用 `window.GenieBridge.sendToGenie(command)`；两条之间留出短间隔供天猫精灵分别解析。
4. `GenieCommand` 对每条独立命令再次检查长度、操作、设备白名单和高风险词；任何一条失败都会形成部分接受或失败回执，不会伪报整组成功。
5. 原生代码调用：

```text
content://com.alibaba.ailabs.genie.assistant.provider/GenieApi
ContentValues: data=<短文本指令>, method=15
```

`ContentResolver.insert()` 返回 `null` 也可能表示 Provider 已正常接受请求，所以客户端只显示“指令已提交”，不能据此宣称设备已经执行成功。

原生层不会先调用 `resolveContentProvider()` 判断可用性。该查询在 T10S 上可能受 Android 包可见性影响而返回空，但普通第三方 UID 直接 `insert()` 已经真机验证可用；因此现在以实际调用结果为准。

v1.1.2 沿用音乐播放器、空调、风扇等低风险白名单。Agent 可按温度、天气和用户补充要求选择或组合这些设备，但原生层不根据“累了/想放松”自行猜测动作，只执行服务端规划且经用户确认后的明确短命令。诸如先建议音乐、用户再说“需要并且帮我打开空调”，会保留音乐并重新确认；确认后先向 `GenieApi / method=15` 提交音乐，再独立提交空调。只有用户明确说“改成/换成/只要/不需要原方案而是……”才替换原建议。

WebView 在播放 Omni PCM 回答期间会暂停麦克风上传，播放队列清空后再等待扬声器尾音结束才恢复采集，避免设备把自身播报回灌为用户语音。原生桥另通过 `AudioManager.isMusicActive()` 告知 WebView 当前是否播放音乐：非音乐状态可使用受限远场软件增益，播放音乐时增益固定为 1.0，仅保留系统 AEC/降噪，避免放大音乐残声。

当前不实现“由第三方 APK 暂停天猫精灵系统热词监听”的麦克风所有权交接。真机包信息表明本应用是普通 UID `10047`，当前公开可用的 `GenieApi / method=15` 只接收文字指令；Android `AudioFocus` 管理扬声器播放而不是录音所有权，`VOICE_COMMUNICATION` 采集也不能作为暂停特权系统助手的控制协议。未获得厂商正式 Binder/Provider/API 与恢复约定前，不发送猜测性指令、不停止系统包服务，也不申请无障碍或系统权限。

## 安全边界

- App 运行时不执行 ADB、不进入终端、不申请 root 或无障碍权限。
- `adb shell content insert ...` 仅是开发期验证上述 Android API 的等价命令。
- 当前允许灯光/照明、空调/新风、窗帘、电视/投影、风扇、空气净化、加湿除湿、扫地机器人和智能插座的明确低风险操作，包括温度、亮度、风速、档位、模式、开合、音量、清扫和回充等自然表达。
- 门锁、燃气、热水器、车库门、监控/摄像头、报警器及高温烹饪/取暖设备等操作直接拒绝。
- H5 浏览器没有 `GenieBridge`，会在能力握手时报告 `genie_provider=false`。

## 构建

环境使用 JDK 17、Android SDK `D:\Android-SDK` 和与 Android Gradle Plugin 兼容的 Gradle 9.6.1。当前仓库未提交 Wrapper，可从 Android Studio 执行 `clean`、`assembleDebug` 或 `assembleRelease`；正式包还需要本机忽略目录中的签名配置。

主应用包名为 `com.jpx.tmallsmarthome`，最低 Android 版本为 API 23，T10S 验证环境为 Android 10、1280×800、arm64-v8a。
