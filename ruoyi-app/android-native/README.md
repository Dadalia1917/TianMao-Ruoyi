# 天猫智家 Android 原生容器

**产品版本：v1.1.0 · 文档更新时间：2026 年 8 月 13 日 11:07:12（UTC+8）**

该工程把 `ruoyi-app` 的 H5 产物装入 Android WebView，并为天猫精灵智慧屏 T10S 提供麦克风、开机拉起和本机智能家居指令桥接。

## T10S 家居指令链路

1. WebView 在 `client.hello` 中声明 `capabilities.genie_provider=true`。
2. FastAPI 只从 Qwen 最终用户转写中提取明确、低风险的设备操作，并下发 `assistant.home_command.pending` 结构化事件。
3. `index-voice-bridge.js` 调用 `window.GenieBridge.sendToGenie(command)`。
4. `GenieCommand` 再次检查长度、操作、设备白名单和高风险词。
5. 原生代码调用：

```text
content://com.alibaba.ailabs.genie.assistant.provider/GenieApi
ContentValues: data=<短文本指令>, method=15
```

`ContentResolver.insert()` 返回 `null` 也可能表示 Provider 已正常接受请求，所以客户端只显示“指令已提交”，不能据此宣称设备已经执行成功。

## 安全边界

- App 运行时不执行 ADB、不进入终端、不申请 root 或无障碍权限。
- `adb shell content insert ...` 仅是开发期验证上述 Android API 的等价命令。
- 当前只允许灯、空调、窗帘、电视、风扇、空气净化器和普通插座的明确低风险操作。
- 门锁、燃气、热水器、车库门、监控撤防和报警器等操作直接拒绝。
- H5 浏览器没有 `GenieBridge`，会在能力握手时报告 `genie_provider=false`。

## 构建

环境使用 JDK 17、Android SDK `D:\Android-SDK` 和与 Android Gradle Plugin 兼容的 Gradle 9.6.1。当前仓库未提交 Wrapper，可从 Android Studio 执行 `clean`、`assembleDebug` 或 `assembleRelease`；正式包还需要本机忽略目录中的签名配置。

主应用包名为 `com.jpx.tmallsmarthome`，最低 Android 版本为 API 23，T10S 验证环境为 Android 10、1280×800、arm64-v8a。
