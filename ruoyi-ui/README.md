# 天猫智家运营平台 / Tmall Smart Home Operations Console

**产品版本：v1.0.0 · 文档日期：2026 年 8 月 11 日**

本目录是“天猫智家·千问智能语音助手”的内部运营后台，不是消费者端 APP。普通用户只使用 `ruoyi-app`；运营人员在本后台查看语音会话、服务状态、账号长期记忆和消费者账号。

This directory contains the internal operations console for the Tmall Smart Home Qwen Voice Assistant. The consumer client lives in `ruoyi-app`.

## 开发启动

```powershell
npm install
npm run dev
```

- 管理端开发地址：`http://127.0.0.1:9091`
- Java API：`http://127.0.0.1:8080`
- HBuilderX H5 客户端：`http://127.0.0.1:9090`

开发端口不再使用 `80`，因此 Windows 下无需管理员权限。接口代理在 `vite.config.js` 中配置；生产环境应由 Nginx 或统一网关转发。

## 主要页面

- `src/views/index.vue`：语音助手运营总览。
- `src/views/assistant/session/index.vue`：实时语音会话、状态、时长与失败原因。
- `src/views/assistant/memory/index.vue`：按账号隔离的长期记忆审查与逻辑删除。
- `src/views/system/user/`：消费者和运营账号管理。
- `src/views/login.vue`：运营人员登录页。

## 数据与权限

对应后端接口位于 `/assistant/overview`、`/assistant/session/list` 和 `/assistant/memory/list`。菜单与权限由 `sql/ry-cat.sql` 初始化；旧数据库执行 `sql/tmall-smart-home-assistant-upgrade.sql`。

运营后台不播放或下载原始录音，因为服务端默认不保存原始音频。删除长期记忆采用逻辑删除，新会话不再注入被删除内容，但仍保留必要审计痕迹。

## 构建与安全检查

```powershell
npm run build:prod
npm audit
```

项目使用内置 SVG 雪碧图插件，避免引入旧 `vite-plugin-svg-icons` 的脆弱依赖链。不要在前端源码、环境文件或构建产物中写入百炼 API Key、数据库密码或生产 Token。
