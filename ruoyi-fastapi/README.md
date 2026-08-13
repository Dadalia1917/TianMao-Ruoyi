# 天猫智家实时语音服务

**产品版本：v1.1.0 · 文档更新时间：2026 年 8 月 13 日（UTC+8）**

完整的软件说明、技术栈、UML、ER 图、接口总表和部署指南请阅读仓库根目录 `README.md`。

当前版本负责已登录用户的实时语音对话、六模型文字对话、自动续接、账号长期记忆和智能家居 Agent。v1.1.0 使用 LangGraph 单总控编排、Qwen Function Calling、确定性安全策略与环境工具，把低风险家居计划转换为结构化事件；T10S 客户端收到事件后，通过 Android `ContentResolver` 调用本机天猫精灵 `ContentProvider`。外部天猫精灵声学转发仅作为可选兼容实验，默认关闭。当前尚未接入 Home Assistant，后续可把真实设备状态工具接入现有 Agent，不需要改变移动端事件协议。

## 一键启动

推荐 Python 3.11 或 3.12。Docker 固定使用 Python 3.11；暂不建议用 Python 3.14 运行 LangGraph/LangChain Core。

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
- Agent 能力目录：`GET http://127.0.0.1:8001/api/v1/agent/capabilities`
- Agent 规划调试：`POST http://127.0.0.1:8001/api/v1/agent/plan`（需要 RuoYi Token，只返回计划，不直接越过客户端执行）

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

- `GET /api/v1/memories 404`：通常是修改源码后仍在运行旧 FastAPI 进程。结束原来的 `main.py`，重新启动后确认根接口返回当前产品版本 `1.1.0`，并在 `/docs` 中看到记忆路由。`OPTIONS 200` 只说明 CORS 中间件响应正常，不能证明业务路由已加载。
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
- `GENIE_PROVIDER_ENABLED`：是否向声明支持本机天猫精灵 Provider 的客户端发送低风险家居命令事件，默认开启。
- `ACOUSTIC_RELAY_ENABLED`：是否启用外部天猫精灵声学转发实验功能，默认关闭；只有本机 Provider 不可用且明确需要兼容实验时才开启。
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
- `AGENT_ENABLED`：智能家居 Agent 总开关，默认开启。
- `AGENT_MODEL` / `AGENT_API_URL`：用于 Function Calling 的百炼模型与兼容接口。
- `AGENT_TIMEOUT_SECONDS` / `AGENT_MAX_TOOL_ROUNDS`：单次规划超时与最大工具轮数；限制 ReAct 循环，避免语音链路久等。
- `AGENT_LOCATION_NAME` / `AGENT_LATITUDE` / `AGENT_LONGITUDE` / `AGENT_TIMEZONE`：天气工具所在地配置。
- `AGENT_WEATHER_ENABLED`：空调建议是否读取实时天气。
- `AGENT_SIMULATED_ENVIRONMENT_ENABLED`：灯光是否使用明确标记为“模拟”的室内照度；接入真实传感器后应关闭。

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

## 智能家居 Agent

v1.1.0 已把 Agent 作为 FastAPI 内部独立模块落地，代码位于 `assistant_server/agent/`。架构采用一个 LangGraph 总控 Agent 和少量有边界的工具，而不是为天气、灯光、空调各启动一个会互相聊天的 Agent：这样能减少实时语音延迟、重复推理和不一致决策。

```text
Omni 最终转写
  -> 家居意图预筛（普通聊天仍走实时直连）
  -> LangGraph：分析 -> 风险/澄清/直接/环境规划 -> 最终校验
  -> 天气工具或模拟照度工具
  -> Qwen Function Calling 提交严格 ModelPlan
  -> assistant.home_command.pending
  -> WebView GenieBridge -> Android ContentResolver -> GenieApi
```

执行约束：

- 只有最终状态为 `execute` 才会向 Android 发送指令；`advise`、`clarify`、`blocked`、`not_applicable` 和异常均不会执行。
- 门锁、燃气、烹饪加热和安防等高风险设备在模型调用前即被确定性策略拦截。
- 空调在用户未指定温度时先查询当地天气；灯光在没有真实传感器时使用低可信、明确标记为模拟的照度。
- 用户明确给出的安全参数优先；长期记忆仅作为偏好参考，不能充当授权、不能覆盖本轮命令或安全规则。
- 模型输出必须通过 Pydantic 严格结构校验、设备一致性检查和温度/亮度范围裁剪。
- Provider 接收只能表示“已提交”，不能宣称灯或空调已经成功动作。

项目只直接依赖 `langgraph`，不需要安装完整 `langchain`；测试也使用 `asyncio.run()`，不要求 `pytest-asyncio`。Dify 可保留给未来运营人员配置知识库或非实时流程，不进入当前低延迟语音控制主链路。
