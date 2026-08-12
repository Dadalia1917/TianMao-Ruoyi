# 天猫智家实时语音服务

**产品版本：v1.0.0 · 文档日期：2026 年 8 月 11 日**

完整的软件说明、技术栈、UML、ER 图、接口总表和部署指南请阅读仓库根目录 `README.md`。

当前版本负责已登录用户的实时语音对话、六模型文字对话、自动续接和账号长期记忆，尚未直接接入 Home Assistant。过渡阶段可开启“外部天猫精灵声学转发”：模型把明确的低风险家居请求规范化为“天猫精灵，打开卧室灯”一类短命令，由本机扬声器转达给附近另一台天猫精灵；它不等同于可靠的设备控制，也不会伪造执行结果。后续 Agent 层可在服务端独立扩展，不需要改动移动端协议。

## 一键启动

Python 需要 3.11 或更高版本。

```powershell
cd E:\无锡捷普迅智能科技有限公司\天猫精灵\天猫精灵安卓APK\RuoYi\ruoyi-fastapi
pip install -r requirements.txt
Copy-Item .env.example .env
# 编辑 .env，填写 DASHSCOPE_API_KEY，并确认若依 /getInfo 地址
# 旧数据库升级时执行 ..\sql\tmall-smart-home-assistant-upgrade.sql
python main.py
```

启动后可访问：

- 服务状态：`http://127.0.0.1:8001/health/ready`
- 接口文档：`http://127.0.0.1:8001/docs`
- 实时语音：`ws://127.0.0.1:8001/ws/v1/assistant`
- 文字对话：`ws://127.0.0.1:8001/ws/v1/text-chat`
- 文字模型目录：`GET http://127.0.0.1:8001/api/v1/text-models`（需要 RuoYi Token）

`main.py` 会自动读取同目录下的 `.env`；`.env` 已被 `.gitignore` 排除，API Key 不会进入源码。
若已有语音会话表但缺少 `ai_user_memory`，服务会自动创建这张助手自管表，便于开发环境一键启动。

## HBuilderX H5 查看

1. 在 HBuilderX 中打开 `RuoYi/ruoyi-app`。
2. 运行到浏览器（H5）。本机预览默认连接 `http://127.0.0.1:8001`。
3. 先启动 RuoYi、Redis 和 FastAPI，登录后点击“开始”，浏览器会请求麦克风权限。
4. 如需用同一局域网内的手机访问 H5，由开发人员把 `ruoyi-app/config.js` 的 AI 网关地址改成运行 FastAPI 的电脑 IP，例如 `http://192.168.3.180:8001`。

消费者界面不提供 FastAPI 地址编辑入口。正式发布前必须由部署人员在构建配置中写入统一的 HTTPS/WSS 生产网关，避免普通用户误改服务地址。

浏览器麦克风只允许安全上下文：`localhost` 可直接使用；局域网或线上域名建议给 H5 和 FastAPI 都配置 HTTPS/WSS。

## 常见开发问题

- `GET /api/v1/memories 404`：通常是修改源码后仍在运行旧 FastAPI 进程。结束原来的 `main.py`，重新启动后确认根接口返回当前产品版本 `1.0.0`，并在 `/docs` 中看到记忆路由。`OPTIONS 200` 只说明 CORS 中间件响应正常，不能证明业务路由已加载。
- 浏览器提示 `ScriptProcessorNode is deprecated`：这是 AudioWorklet 静态文件未加载时的兼容回退警告，不会中断语音。停止并重新运行 HBuilderX H5、执行一次强制刷新；当前页面会尝试应用路径、站点根路径和 Blob 三种方式加载 AudioWorklet。

## 实时链路

```text
浏览器麦克风
  -> 16 kHz / 16-bit / 单声道 PCM
  -> FastAPI WebSocket（鉴权、限流、背压）
  -> 千问 qwen3.5-omni-plus-realtime
  -> 24 kHz PCM + 双向文字转录
  -> Web Audio 连续播放
```

页面支持：

- 服务端语义 VAD，自然判断用户说话结束；
- 用户开口时取消当前回复并清空播放队列，实现打断；
- 回声消除、降噪、自动增益；
- “天猫管家”作为唤醒口令：单独呼喊时固定回答“姥爷，我在”，后接具体问题时直接回答问题；
- 麦克风静音、通话结束、连接异常提示；
- 20 秒客户端心跳、断线指数退避重连和上游会话无感轮换；
- 用户与助手实时字幕；
- 账号长期记忆注入，以及短暂重连时的最近对话交接；
- 手机竖屏、平板和中控横屏自适应布局。

## 文字对话与语音播报

`/ws/v1/text-chat` 把六个模型统一为同一套流式事件：`text.reasoning.delta` 返回思考过程，`text.answer.delta` 返回最终答案，`text.done` 表示完成。当前工控屏产品只接收纯文字上下文，不接收或转发图片附件。

- `qwen3.8-max` → `Qwen3.8-Max`
- `qwen3.7-plus-2026-05-26` → `Qwen3.7-Plus`
- `qwen3.7-flash-2026-07-15` → `Qwen3.7-Flash`
- `deepseek-v4-pro` → `DeepSeek-V4-Pro`
- `deepseek-v4-flash-0731` → `DeepSeek-V4-Flash`
- `deepseek-r1-0528` → `DeepSeek-R1`

除固定思考模式的 DeepSeek-R1 外，网关会为其余模型传入 `enable_thinking=true`。实际模型 ID 均可通过 `.env` 的 `TEXT_MODEL_*` 替换，不需要改前端展示名。H5 的语音识别和播报位于客户端，识别结果仍按普通文字请求发给这里。

## 配置项

主要配置都在 `.env.example`：

- `DASHSCOPE_REALTIME_URL`：用户示例中的公网地址可以直接保留；若百炼控制台要求业务空间域名，改成带 `WorkspaceId` 的地址。
- `MAX_CONNECTIONS`：单进程并发 WebSocket 上限，默认 300。
- `MAX_CONNECTIONS_PER_USER`：单账号会话上限，默认 3。
- `UPSTREAM_ROTATE_SECONDS`：千问单连接主动轮换时间，默认 6900 秒；客户端会自动续接。
- `ACOUSTIC_RELAY_ENABLED`：是否启用外部天猫精灵声学转发实验功能，默认开启；接入 Home Assistant 后应关闭。
- `ACOUSTIC_RELAY_WAKE_PHRASE`：外部设备唤醒词，默认 `天猫精灵`。
- `RUOYI_AUTH_URL`：RuoYi 的 `/getInfo` 完整地址；每次语音建连都必须通过账号校验。
- `DATABASE_ENABLED`：是否启用 MySQL；`MEMORY_ENABLED=true` 时必须开启。
- `VOICE_STORE_TRANSCRIPTS`：是否额外写入完整转录文字，默认关闭。
- `MEMORY_ENABLED`：账号长期记忆开关，默认开启。
- `MEMORY_MODEL`：记忆提取文本模型，默认 `qwen-plus`。
- `MEMORY_WORKERS` / `MEMORY_QUEUE_SIZE`：异步记忆任务的并发数和有界队列大小。
- `TEXT_CHAT_ENABLED` / `TEXT_CHAT_API_URL`：文字模型网关开关与百炼兼容接口地址。
- `TEXT_MODEL_*`：六种文字模型的真实模型 ID。
- `TEXT_MAX_CONNECTIONS` / `TEXT_MAX_CONNECTIONS_PER_USER`：文字请求并发上限。

## 登录与记录

移动端首条 WebSocket 消息会携带 RuoYi Token。FastAPI 调用 `RUOYI_AUTH_URL` 获取用户 ID，再按账号执行并发隔离和可选数据库记录；缺少或失效 Token 会返回 `unauthorized`，APP 随后回到登录页。

可选 MySQL 表位于 `sql/ry-cat.sql` 和 `sql/tmall-smart-home-assistant-upgrade.sql`：

- `ai_voice_session`：账号、模型、时长、消息计数和关闭原因，不保存原始音频；
- `ai_voice_message`：完整文字转录，仅 `VOICE_STORE_TRANSCRIPTS=true` 时写入；
- `ai_user_memory`：按用户隔离的稳定偏好、资料、习惯、关系和目标。

每次语音链路结束后，`MemoryManager` 把文本快照放入有界异步队列，由 `qwen-plus` 以 JSON 模式提取稳定事实并执行幂等 upsert。实时 WebSocket 不等待提取结果。新会话只注入数量受限的账号记忆，并把记忆明确标记为“不可信事实背景”，避免其中的文字覆盖系统指令。密码、密钥、验证码、精确住址和金融标识等内容不应进入长期记忆。

APP 的可回看历史默认保存在设备本地并按 RuoYi 用户 ID 分区，因此不开启 FastAPI 数据库也能使用记录界面。

服务是全异步实现，不在服务端打开声卡，也不为每个用户创建线程。每个会话只维护手机和千问之间的两个 WebSocket 泵，并对手机下行使用有界队列，避免慢客户端无限占用内存。记忆提取使用单独的有界队列，不与音频转发争用请求生命周期。生产环境可在 Caddy/负载均衡后运行多个进程或容器，并按百炼账号实际并发额度设置总上限。

“持续待命”通过自动续接实现，并不绕过云模型的单连接上限。默认在官方 120 分钟上限前 5 分钟轮换；外部长期记忆也用于弥补模型只保留最近 100 个音频轮次或累计 600 秒上下文的限制，详见[百炼 Realtime 使用限制](https://help.aliyun.com/zh/model-studio/realtime)。H5 页面处于前台时可以持续工作；浏览器/手机系统可能暂停后台网页。后续打包 APK 若要求锁屏和后台常驻，需要增加 Android 前台服务、持续通知和相应麦克风权限合规说明。

## 后续 Agent 接口边界

当前记忆模块刻意不引入 LangChain/LangGraph，以降低实时链路依赖和运行开销。后续确定 Dify、LangChain 或 LangGraph 后，建议作为独立的“对话编排/工具执行”模块接在 FastAPI 服务端。移动端继续只处理音频和标准状态事件；不要把 Agent 密钥、Home Assistant Token 或工具执行逻辑放入 H5/APK。
