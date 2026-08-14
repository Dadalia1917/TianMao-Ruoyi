# 天猫智家·千问智能语音助手

> **Tmall Smart Home Qwen Voice Assistant**

面向天猫智慧工控屏、Android 终端和 H5 的实时语音助手系统。项目在 RuoYi 前后端分离框架基础上，接入阿里云百炼 Qwen3.5 Omni 实时语音模型，提供账号体系、实时双向语音、文字对话、跨会话长期记忆、T10S 本机低风险智能家居指令、消费者端应用和运营管理后台。

| 项目属性 | 当前值 |
| --- | --- |
| 产品名称 | 天猫智家·千问智能语音助手 |
| English name | Tmall Smart Home Qwen Voice Assistant |
| 产品版本 | **v1.1.0** |
| 版本更新时间 | **2026 年 8 月 14 日 18:22:47（UTC+8）** |
| 当前阶段 | v1.1.0 已增加硬唤醒门控、语音退下、家庭实时状态与情境决策；T10S 控制、回声抑制、悬浮入口及真实重启链路均已完成验证 |
| 适用终端 | 天猫智慧工控屏、Android、桌面 H5 |
| 开发单位 | 无锡捷普迅智能科技有限公司 |
| 基础框架 | RuoYi 3.9.2 派生工程 |

> 版本说明：**v1.1.0 是本产品版本**；Maven 和 ruoyi-ui 中的 3.9.2 是继承的 RuoYi 工程/依赖版本，两者含义不同，不应互相替换。

## 文档导航

- [v1.1.0 更新说明](#1-v110-更新说明)
- [软件说明与需求](#2-软件说明)
- [UML 用例图](#4-uml-用例图)
- [总体架构与软件工程图](#5-总体架构)
- [UML 时序图、状态图与领域类图](#6-uml-核心时序图)
- [ER 图与数据设计](#9-er-图与数据设计)
- [技术栈与仓库结构](#10-技术栈)
- [核心接口](#12-核心接口)
- [本地开发、部署与配置](#13-本地开发与启动)
- [并发、安全、测试与后续路线](#15-高并发与解耦设计)
- [开发交接约定](#19-开发交接约定)
- [APK 打包前待办清单](#22-v101-待办apk-打包前问题清单)

---

## 1. v1.1.0 更新说明

版本更新时间：**2026 年 8 月 14 日 18:22:47（UTC+8）**

v1.1.0 在不改变实时语音、文字对话、账号、长期记忆和运营后台既有功能的前提下，完成 T10S 本机天猫精灵 `ContentProvider` 控制链路重构，并在 FastAPI 内落地智能家居 Agent 基线。

### 1.1 v1.1.0 功能变更

- FastAPI 从 Omni 最终语音转写中识别明确、低风险的通用家居控制请求，并向具备原生能力的客户端发送结构化事件。当前覆盖灯光/照明、空调/新风、窗帘/纱帘/百叶帘、电视/投影、风扇、空气净化、加湿除湿、扫地机器人和智能插座，房间名、设备名、温度、亮度、风速、档位和模式会原样交给天猫精灵解析。
- uni-app 通过可信本地 WebView 的 `GenieBridge` 把结构化命令交给 Android 原生层；H5 浏览器不会声明或调用该设备能力。
- Android 原生层使用 `ContentResolver.insert()` 调用 `content://com.alibaba.ailabs.genie.assistant.provider/GenieApi`，不在运行时进入终端、不执行 ADB、不要求 root 或无障碍权限。
- 移除 `PackageManager.resolveContentProvider()` 元数据预检，直接调用已由普通第三方 UID 探针验证可用的 `GenieApi`，避免 Android 包可见性造成“预检失败、实际可调用”的误判。
- T10S 实时语音在播放回答期间暂停麦克风上行，并在播报完成后保留扬声器尾音保护，防止 Omni 把自己的回答重新识别成下一轮用户问题。
- 实时连接建立后默认处于“等待唤醒”，服务端 VAD/ASR 仅用于识别句首口令“管家”；“天猫管家”“曼巴管家”等旧口令不再唤醒。休眠期间的其他谈话会被丢弃并从上游上下文删除，不会触发模型回答或进入历史记录。单独呼喊“管家”固定回答“我在，有什么需要？”，口令后可直接附带问题。
- 唤醒后进入连续对话；识别到“你可以退下了”“我不想跟你说话了”“结束对话”“先这样吧”“再见”等明确结束语时，固定简短回应后关闭本轮对话并恢复休眠。再次对话必须重新说“管家”。
- 语音主页的中央聆听球已补充状态化动效：待命时柔和呼吸，唤醒/聆听时放大并产生冰蓝色波纹，思考和播报阶段使用独立的流动与脉冲反馈。
- 唤醒与结束由 FastAPI 状态机决定，而不是仅靠提示词约束；百炼会话关闭自动响应，由代理在通过门控后显式创建回复，避免模型误响应环境谈话。
- 智能家居指令会从“帮我打开天猫精灵，让天猫精灵开灯”等复合句中只提取实际设备命令“开灯”，不再把唤醒或转述前缀传给天猫精灵。
- 服务端与 Android 原生层均执行低风险白名单校验；门锁、燃气、热水器、车库、监控、布撤防等高风险请求以及含糊、否定、询问状态类语句不会下发。
- UI 仅反馈“已提交/提交失败”，不把 Provider 接收请求误报为设备已经执行成功。
- 外部天猫精灵声学转发保留为可选兼容实验，但默认关闭；支持本机 Provider 时不通过扬声器唤醒另一台设备。
- Docker Compose、FastAPI 服务版本、uni-app、Android 原生工程和隐私协议统一升级至 v1.1.0。
- 新增 `assistant_server/agent/`：使用 LangGraph `StateGraph` 实现“分析、风险分流、环境取证、Function Calling、最终校验”的单总控工作流。普通对话仍直连 Qwen3.5 Omni，只有家居操作意图才进入 Agent，避免增加所有语音请求的延迟。
- 空调在用户未指定温度时先获取当地天气再推荐 16～30℃ 范围内的参数；灯光在尚无真实传感器时使用明确标记为模拟、低可信的照度数据推荐 1%～100% 亮度。用户明确给出的安全参数不会被偏好记忆擅自覆盖。
- Agent 通过 Qwen Function Calling 调用有界工具并生成严格 Pydantic 计划；`execute` 状态只生成待确认建议，先播报家庭状态、依据、参数和拟执行动作。只有用户随后明确同意才触发 T10S，拒绝会取消并回到待命，含糊答复会要求“执行/取消”二选一；建议、澄清、拦截、不适用或规划异常均不执行。
- 长期记忆作为偏好参考注入 Agent，但不能作为权限授权、设备实况或安全规则；全部工具调用、证据和最终决策保留结构化日志字段，便于后续审计。
- 当前采用“一个总控 Agent + 有界工具”，没有拆成多个互相对话的 Agent。Dify 仅作为未来知识库/非实时运营流程的可选补充，不进入实时语音主链路。
- 新增短时“家庭状态”层和按账号/房间隔离的状态接口，可接收室温、湿度、照度、人体存在及空调等设备状态。用户说“我有点热”“屋里太暗”等隐式诉求时，Agent 会先收集室内状态、室外天气、当前时间段和长期偏好，再决定是否执行以及使用什么参数。
- Agent 回复中附带可审计的决策依据摘要，例如“客厅 28℃、湿度 68%、室外 35℃、空调关闭、偏好 25℃”，不伪造传感器数据，也不向客户端泄露模型内部隐藏推理文本。没有真实传感器数据时，模拟值会明确标记为低可信来源。
- 家庭实时状态默认 300 秒过期；生产 Docker 复用 Redis 7 存放短时状态，使两个 FastAPI Worker 能读取同一份家庭状态。本地未配置 Redis 时自动降级到单进程内存。
- 本次没有新增 MySQL 表或修改持久化数据模型，不需要执行数据库升级脚本；Home Assistant 或硬件网关后续只需持续调用家庭状态接口刷新实时数据。
- T10S 开机后不再自动打开完整助手页面。`BOOT_COMPLETED` 先拉起 1×1 透明引导 Activity，再启动前台悬浮窗服务并立即返回天猫精灵桌面；悬浮球使用项目老鼠品牌图标，用户首次点击后进入正式 APP。
- 原生容器在助手首次启动后维持 WebView、麦克风与 WebSocket 运行；返回天猫精灵主页或切到后台时仍可监听“管家”。语音主页底部操作栏已移除，右上角退出按钮只回到天猫精灵主页，不结束助手常驻运行。

### 1.2 v1.1.0 验证与产物

- FastAPI 自动化测试通过：78 项（包含严格硬唤醒匹配、休眠语句忽略、明确退下语义、待确认执行/取消/含糊答复、隐式冷热诉求、家庭状态合并/清理、多类家居自然表达、高风险拦截、天气温度推荐、模拟照度推荐和用户明确参数优先）。
- uni-app H5 与 App 生产构建通过。
- Android Release 构建与 APK 签名验证通过；包名保持 `com.jpx.tmallsmarthome`，`versionCode=110`，便于覆盖升级 v1.0.0。
- Docker Compose 配置校验通过。
- 正式安装包：`ruoyi-app/apk/天猫智家语音助手-v1.1.0.apk`。
- APK SHA-256：`661325B361B7E977F8F040A1B3B55CA056CE71189CB23E761FD17BD891CE576F`。
- 2026 年 8 月 14 日 18:22:47（UTC+8）已完成 v1.1.0 正式包重建、v1/v2 签名校验和 T10S 覆盖安装；当前正式包进程可正常拉起且未发现崩溃。阿里云 FastAPI 实时语音服务已同步更新，FastAPI 与 Java 容器均保持健康。

### 1.3 v1.0.0 历史基线

发布日期：**2026 年 8 月 11 日**

本版本形成了可继续交付给 Claude Code、Cursor 或其他开发人员维护的首个软件工程基线。

#### v1.0.0 消费者端

- 完成“天猫智家”统一品牌、登录、注册、用户服务协议和隐私政策页面。
- 登录身份在本机保留；连续 30 天未打开应用后要求重新登录。
- 登录后进入 Qwen3.5 Omni 实时语音助手，支持自动连接、持续待命、服务端 VAD、语音打断、实时转写和语音播报。
- 支持严格的“管家”唤醒语义；单独说出唤醒词时固定回复“我在”。
- 增加 T10S 本机智能家居控制链路：服务端从最终语音转写中提取明确、低风险的灯、空调、窗帘等指令，经 WebSocket 结构化事件交给 Android 原生桥，再由 `ContentResolver` 调用天猫精灵导出的 `ContentProvider`。
- 保留可配置的“外部天猫精灵声学转发”作为兼容回退，默认关闭；本机 Provider 可用时不再让 Omni 通过扬声器喊另一台设备。
- 用户询问模型身份时如实回答当前模型身份，不用应用品牌冒充基础模型。
- 支持本机语音会话记录、搜索、详情查看和删除。
- 支持按账号隔离的跨会话长期记忆，并提供查看和删除入口。
- 提供次要的文字对话页面，支持键盘输入或麦克风语音提问及自动播报。
- 文字模型可选 Qwen3.8-Max、Qwen3.7-Plus、Qwen3.7-Flash、DeepSeek-V4-Pro、DeepSeek-V4-Flash 和 DeepSeek-R1。
- H5 页面已进行桌面、工控屏和移动端响应式适配。
- 已生成独立签名的 Android 正式包 `天猫智家语音助手-v1.0.0.apk`，包名为 `com.jpx.tmallsmarthome`。
- 已在 Android 10、1280×800、arm64-v8a 的天猫精灵智慧屏 T10S 上完成安装、登录、麦克风、实时 WebSocket 和语音回复验收。

#### v1.0.0 服务端与运营后台

- 新增独立 FastAPI AI 网关，负责百炼实时 WebSocket 转发、文字模型流式响应、认证校验、限流、持久化和长期记忆。
- Java 服务继续承担 RuoYi 账号、权限、验证码、注册、审计和运营查询。
- MySQL 新增语音会话、语音消息和账号长期记忆表。
- 运营后台调整为“天猫智家”主题，增加运营首页、语音会话和长期记忆管理。
- 移除本项目不使用的代码生成器、Quartz 定时任务模块及对应业务表。
- 默认不保存原始录音；语音转写内容的服务端保存默认关闭。
- FastAPI 支持进程级连接上限、单账号连接上限、异步数据库写队列、健康检查和 Prometheus 文本指标。
- 完成阿里云 ECS Docker Compose 部署；Android 本地 WebView 的空 Origin、`file://` Origin 与回环开发来源可安全通过握手，账号身份仍由 RuoYi Token 校验。

#### v1.0.0 明确不包含

- 图片、文件或摄像头附件上传。
- Home Assistant 通用接入、设备状态闭环、复杂自动化场景以及门锁、燃气、安防等高风险操作。
- 当前 v1.1.0 之后新增的 LangGraph Agent 基线不属于 v1.0.0 历史范围；Dify 可视化工作流和 Home Assistant 工具仍未接入。
- 天猫精灵技能平台的正式发布配置及硬件厂商侧唤醒链路。
- 应用商店发布、生产域名和生产证书。

以上内容是 v1.0.0 的历史范围说明。v1.1.0 已落地 LangGraph Agent 基线与 T10S Provider 指令闭环；Home Assistant、真实传感器和生产发布仍属于后续版本范围。

> 2026 年 8 月 13 日补充：已在 T10S 上用普通第三方 APK 身份验证 `com.alibaba.ailabs.genie.assistant.provider/GenieApi` 可由 `ContentResolver.insert()` 直接提交文字指令，不要求 root、运行时 ADB、终端或无障碍权限。ADB 的 `content insert` 只用于开发期验证同一个 Android API。当前主应用源码、FastAPI 测试、H5 构建和 Android Debug 构建已通过；由于目标 T10S 暂不在现场，集成后的主应用仍需补一次真机端到端验收。Provider 接受指令不等于设备必然执行成功，因此 UI 和模型只能表述“已提交/正在处理”。

---

## 2. 软件说明

### 2.1 建设目标

让普通消费者通过语音自然地与 AI 对话：

1. 设备开机后常驻悬浮入口，用户点击后进入应用。
2. 应用读取本机有效登录身份并进入语音助手。
3. 麦克风音频实时发送至 Qwen3.5 Omni。
4. 模型返回文字和 PCM 音频，客户端实时播报。
5. 明确的低风险家居控制转为结构化事件，并在 T10S 本机提交给天猫精灵处理。
6. 会话结束后提取稳定偏好或事实，供下一次新会话使用。

系统面向消费者，因此 API 地址、密钥、模型网关等技术参数不在普通用户界面暴露，由部署人员统一配置。

### 2.2 用户角色

| 角色 | 主要职责 |
| --- | --- |
| 消费者 | 注册/登录、语音对话、文字对话、查看本机记录、管理自己的长期记忆 |
| 平台管理员 | 查看运营概览、语音会话状态、长期记忆、账号与权限、登录及操作日志 |
| 运营人员 | 查询服务使用情况和异常会话，不接触原始录音 |
| 天猫精灵/系统启动器 | 通过应用包名或 URL Scheme 拉起消费者端 |
| 阿里云百炼 | 提供 Qwen/DeepSeek 模型推理和实时音频服务 |

### 2.3 功能边界

| 能力 | 状态 | 数据位置 |
| --- | --- | --- |
| 账号登录与注册 | 已实现 | Java + MySQL + Redis |
| 30 天本机身份有效期 | 已实现 | 客户端安全存储 |
| Qwen3.5 Omni 实时语音 | 已实现 | FastAPI WebSocket 代理 |
| 实时转写与语音播报 | 已实现 | 内存流式处理 |
| 本机对话记录 | 已实现 | 客户端按账号隔离 |
| 跨会话长期记忆 | 已实现 | MySQL 按账号隔离 |
| 多模型文字对话 | 已实现 | FastAPI 流式代理 |
| T10S 低风险家居指令提交 | 已实现，待主应用最终真机验收 | Android JSBridge + 天猫精灵 ContentProvider |
| 运营后台 | 已实现 | Vue 3 + Java |
| 原始录音保存 | 不实现 | 默认不落盘 |
| 图片/附件 | 不实现 | 无 |
| 家庭实时状态接收与情境决策 | 已实现 | Redis 短时状态；本地可降级内存 |
| Home Assistant 自动采集、设备执行回执与复杂场景 | 后续版本 | 复用现有状态接口和 Agent/工具层 |

---

## 3. 软件需求摘要

### 3.1 功能需求

- FR-01：首次使用必须登录或注册；身份过期后重新认证。
- FR-02：登录成功后直接进入当前账号的语音助手。
- FR-03：客户端应支持自动连接、重连、静音、结束、记录查看和新建会话。
- FR-04：用户说话时可打断正在播放的模型语音。
- FR-05：每个账号的记录和长期记忆必须隔离。
- FR-06：新语音会话应自动注入该账号的有效长期记忆。
- FR-07：用户可查看、删除单条或清空自己的长期记忆。
- FR-08：管理员可查询会话、记忆、用户和审计日志。
- FR-09：文字对话可选择已配置模型并以流式方式展示思考摘要和最终回答。
- FR-10：消费者端不展示服务地址、API Key 或数据库配置。
- FR-11：Android 客户端声明本机 Provider 能力后，明确的低风险家居指令应通过结构化事件提交给天猫精灵；H5 不得伪装具备该能力。
- FR-12：门锁、燃气、安防等高风险操作及含糊指令不得跨越原生控制边界。

### 3.2 非功能需求

- NFR-01 安全：API Key 只保存在服务端环境变量，不进入前端包。
- NFR-02 隐私：默认不保存原始录音，转写持久化默认关闭。
- NFR-03 并发：按进程和账号限制连接数，数据库写入异步排队。
- NFR-04 可用性：提供存活、就绪检查和连接自动恢复。
- NFR-05 可维护性：Java、AI 网关、消费者端、运营端四层解耦。
- NFR-06 可移植性：同一消费者端源码可输出 H5，并通过 Android Studio 原生容器生成 Android 正式 APK。
- NFR-07 可观测性：服务日志、运营统计、健康接口和 Prometheus 指标可用。
- NFR-08 响应式：适配桌面 H5、横屏工控屏和移动端。
- NFR-09 最小权限：运行时不执行 ADB、不进入终端、不申请 root；服务端和 Android 原生层分别校验一次家居指令。

---

## 4. UML 用例图

Mermaid 没有独立的用例图语法，以下采用标准参与者—用例关系的 UML 逻辑表达。

~~~mermaid
flowchart LR
    Consumer["参与者：消费者"]
    Admin["参与者：平台管理员/运营人员"]
    Launcher["参与者：天猫精灵或系统启动器"]
    Bailian["外部系统：阿里云百炼"]
    GenieProvider["外部系统：T10S 天猫精灵 Provider"]

    subgraph System["天猫智家·千问智能语音助手"]
        UC_Login(["登录/注册与30天身份保持"])
        UC_Wake(["拉起应用并自动待命"])
        UC_Voice(["实时语音对话"])
        UC_Interrupt(["打断与静音"])
        UC_History(["查看/搜索/删除本机记录"])
        UC_Memory(["查看/删除跨会话记忆"])
        UC_Text(["多模型文字对话"])
        UC_Home(["提交低风险家居指令"])
        UC_Audit(["查询会话与运营数据"])
        UC_Account(["管理用户、角色与权限"])
    end

    Consumer --> UC_Login
    Consumer --> UC_Voice
    Consumer --> UC_Interrupt
    Consumer --> UC_History
    Consumer --> UC_Memory
    Consumer --> UC_Text
    Consumer --> UC_Home
    Launcher --> UC_Wake
    UC_Wake -. "包含" .-> UC_Login
    UC_Wake -. "包含" .-> UC_Voice
    UC_Voice --> Bailian
    UC_Text --> Bailian
    UC_Home --> GenieProvider
    Admin --> UC_Audit
    Admin --> UC_Account
~~~

---

## 5. 总体架构

### 5.1 系统上下文图

~~~mermaid
flowchart LR
    User["消费者"]
    Operator["管理员/运营人员"]
    Tmall["天猫精灵或系统启动器"]
    Client["uni-app 消费者端\nH5 / Android"]
    AdminUI["Vue 3 运营后台"]
    Java["RuoYi Java 服务\n认证 / RBAC / 运营 API"]
    AI["FastAPI AI 网关\n实时语音 / 文本 / 记忆"]
    MySQL[("MySQL 8\n业务与 AI 元数据")]
    Redis[("Redis\nToken 与认证缓存")]
    DashScope["阿里云百炼\nQwen / DeepSeek"]
    GenieProvider["T10S 天猫精灵 ContentProvider\nGenieApi / method=15"]
    HomeDevices["已绑定的灯、空调等设备"]

    User --> Client
    Tmall -->|"包名或 smartbutler://voice"| Client
    Operator --> AdminUI
    Client -->|"HTTPS REST"| Java
    Client <-->|"WSS 双向音频/文本"| AI
    AdminUI -->|"HTTPS REST"| Java
    AI -->|"校验 Token /getInfo"| Java
    Java --> MySQL
    Java --> Redis
    AI --> MySQL
    AI <-->|"百炼 WSS / HTTPS"| DashScope
    AI -->|"结构化低风险指令事件"| Client
    Client -->|"Android JSBridge + ContentResolver"| GenieProvider
    GenieProvider --> HomeDevices
~~~

### 5.2 分层组件图

~~~mermaid
flowchart TB
    subgraph Presentation["表现层"]
        App["ruoyi-app\n消费者端"]
        Web["ruoyi-ui\n运营后台"]
    end

    subgraph Gateway["接口与网关层"]
        JavaAPI["ruoyi-admin\nREST / Spring Security"]
        FastAPI["ruoyi-fastapi\nWebSocket / REST"]
    end

    subgraph Domain["领域与应用层"]
        Auth["账号认证与 RBAC"]
        AssistantOps["语音助手运营服务"]
        Realtime["实时语音代理"]
        TextChat["文字模型代理"]
        Memory["长期记忆提取与注入"]
        History["会话异步持久化"]
        CommandRouter["低风险家居指令路由"]
    end

    subgraph Infrastructure["基础设施层"]
        DB[("MySQL")]
        Cache[("Redis")]
        Models["阿里云百炼模型服务"]
        NativeBridge["Android GenieBridge"]
        Genie["T10S GenieApi Provider"]
    end

    App --> JavaAPI
    App --> FastAPI
    Web --> JavaAPI
    JavaAPI --> Auth
    JavaAPI --> AssistantOps
    FastAPI --> Realtime
    FastAPI --> TextChat
    FastAPI --> Memory
    FastAPI --> History
    FastAPI --> CommandRouter
    Auth --> DB
    Auth --> Cache
    AssistantOps --> DB
    Realtime --> Models
    TextChat --> Models
    Memory --> Models
    Memory --> DB
    History --> DB
    CommandRouter --> App
    App --> NativeBridge
    NativeBridge --> Genie
~~~

### 5.3 部署图

~~~mermaid
flowchart LR
    subgraph Device["消费者设备 / 天猫智慧工控屏"]
        Mic["麦克风"]
        Speaker["扬声器"]
        App["uni-app H5/Android"]
        Local["本机记录\n按账号隔离"]
        Bridge["GenieBridge\n原生双重校验"]
        Provider["天猫精灵 GenieApi\nContentProvider"]
        Mic --> App
        App --> Speaker
        App --> Local
        App --> Bridge
        Bridge --> Provider
    end

    subgraph Edge["生产入口"]
        Proxy["Caddy 2 / HTTPS / WSS\n同域网关与自动证书"]
    end

    subgraph Server["应用服务器"]
        Java1["Java 服务\n容器内 :8080"]
        AI["FastAPI AI 网关\n容器内 :8001 / 多 Worker"]
        ClientStatic["消费者端 H5 静态文件\n站点根路径 /"]
        Admin["运营后台静态文件\n子路径 /admin/"]
    end

    subgraph Data["数据服务"]
        MySQL[("MySQL 8 :3306")]
        Redis[("Redis :6379")]
    end

    Cloud["阿里云百炼"]
    Appliances["灯 / 空调 / 窗帘等\n天猫精灵已绑定设备"]

    App <-->|"HTTPS/WSS"| Proxy
    Proxy --> Java1
    Proxy --> AI
    Proxy --> ClientStatic
    Proxy --> Admin
    Java1 --> MySQL
    Java1 --> Redis
    AI --> MySQL
    AI <--> Cloud
    Provider --> Appliances
~~~

生产部署时，单条 WebSocket 在建立后固定由一个 FastAPI Worker 处理。总连接容量约等于 Worker 数乘以 <code>MAX_CONNECTIONS</code>，但最终容量仍受百炼账号并发配额、CPU、带宽、MySQL 连接池和反向代理限制。

### 5.4 核心数据流图

~~~mermaid
flowchart LR
    Speech["用户语音 PCM 16kHz"] --> Capture["浏览器/Android 采集"]
    Capture --> WS["客户端 WebSocket"]
    WS --> Proxy["FastAPI 鉴权、限流与转发"]
    Proxy --> Omni["Qwen3.5 Omni Realtime"]
    Omni --> Transcript["用户/助手转写"]
    Omni --> Audio["助手 PCM 24kHz"]
    Audio --> Player["客户端实时播放"]
    Transcript --> UI["会话 UI 与本机记录"]
    Transcript --> Queue["异步持久化/记忆队列"]
    Transcript --> Detector["低风险家居意图检测"]
    Detector -->|"结构化 WebSocket 事件"| Bridge["Android GenieBridge"]
    Bridge --> Provider["T10S ContentProvider"]
    Queue --> DB[("MySQL")]
    Queue --> Extractor["长期记忆提取"]
    Extractor --> DB
~~~

---

## 6. UML 核心时序图

### 6.1 登录与进入语音助手

~~~mermaid
sequenceDiagram
    actor U as 消费者
    participant APP as uni-app
    participant JAVA as RuoYi Java
    participant REDIS as Redis
    participant DB as MySQL

    U->>APP: 输入账号、密码、验证码
    APP->>JAVA: POST /login
    JAVA->>DB: 校验账号与密码
    JAVA->>REDIS: 保存登录 Token
    JAVA-->>APP: Token
    APP->>JAVA: GET /getInfo
    JAVA-->>APP: 用户与角色信息
    APP->>APP: 保存 Token 和最近活跃时间
    APP-->>U: 进入天猫智家并自动连接
~~~

### 6.2 实时语音会话

~~~mermaid
sequenceDiagram
    actor U as 消费者
    participant APP as uni-app 音频桥
    participant AI as FastAPI AI 网关
    participant JAVA as RuoYi 鉴权
    participant QWEN as Qwen3.5 Omni
    participant DB as MySQL

    APP->>AI: WSS /ws/v1/assistant + Token
    AI->>JAVA: GET /getInfo
    JAVA-->>AI: 当前账号身份
    AI->>DB: 异步创建 voice_session
    AI->>QWEN: 建立实时会话并注入账号记忆
    QWEN-->>AI: session.created
    AI-->>APP: ready
    loop 实时音频
        U->>APP: 说话
        APP->>AI: PCM16 Base64 音频块
        AI->>QWEN: input_audio_buffer.append
        QWEN-->>AI: 转写 + 回答文字 + PCM24
        AI-->>APP: 文本事件 + 音频事件
        APP-->>U: 展示文字并播放语音
    end
    U->>APP: 结束对话
    APP->>AI: close
    AI->>DB: 更新时长、状态与统计
    AI->>AI: 异步提取稳定长期记忆
    AI->>DB: 合并 ai_user_memory
~~~

### 6.3 T10S 本机家居指令

~~~mermaid
sequenceDiagram
    actor U as 消费者
    participant APP as uni-app 音频桥
    participant AI as FastAPI
    participant QWEN as Qwen3.5 Omni
    participant BRIDGE as Android GenieBridge
    participant GENIE as T10S GenieApi Provider
    participant DEVICE as 已绑定家居设备

    APP->>AI: client.hello(capabilities.genie_provider=true)
    U->>APP: “把客厅灯打开”
    APP->>AI: PCM 音频
    AI->>QWEN: 实时音频转发
    QWEN-->>AI: 最终用户转写
    AI->>AI: Agent 汇总家庭状态、天气、偏好与设备状态
    AI-->>U: 播报依据、参数、拟执行动作并询问是否执行
    U->>APP: “执行”/明确同意
    APP->>AI: 确认语音
    AI->>AI: 待确认状态与二次安全校验
    AI-->>APP: assistant.home_command.pending(command)
    APP->>BRIDGE: sendToGenie(command)
    BRIDGE->>BRIDGE: 长度、设备、动作和高风险词二次校验
    BRIDGE->>GENIE: ContentResolver.insert(data, method=15)
    GENIE-->>BRIDGE: 接受调用（允许返回 null Uri）
    BRIDGE-->>APP: accepted=true（仅代表已提交）
    GENIE->>DEVICE: 天猫精灵解析并尝试执行
~~~

浏览器 H5 的 `genie_provider` 能力为 `false`，不会收到本机控制事件。运行时链路不执行 `adb shell`；ADB 的等价命令仅用于开发人员检查目标系统 Provider 是否存在和可调用。

### 6.4 跨会话长期记忆

~~~mermaid
sequenceDiagram
    participant S1 as 会话 A
    participant M as 记忆服务
    participant LLM as 记忆提取模型
    participant DB as ai_user_memory
    participant S2 as 会话 B

    S1->>M: 会话结束后的有效转写
    M->>LLM: 提取稳定偏好/事实
    LLM-->>M: 结构化候选记忆
    M->>DB: 按 user_id + memory_key 合并
    S2->>DB: 查询当前账号有效记忆
    DB-->>S2: 最近有效记忆
    S2->>S2: 注入 Qwen 实时会话 instructions
~~~

长期记忆是异步、筛选式能力：寒暄和一次性问题通常不会形成记忆；稳定偏好、称呼、长期计划等更可能被提取。用户可在“管家记忆”中核对和删除。

---

## 7. UML 状态图

### 7.1 语音会话状态

~~~mermaid
stateDiagram-v2
    state "待命" as Idle
    state "连接中" as Connecting
    state "休眠监听唤醒词" as Dormant
    state "已唤醒对话" as Active
    state "模型播报" as Speaking
    state "静音" as Muted
    state "自动重连" as Reconnecting
    state "正常结束" as Closed
    state "失败" as Failed

    [*] --> Idle
    Idle --> Connecting: 自动启动/点击开始
    Connecting --> Dormant: 客户端与百炼均就绪
    Connecting --> Reconnecting: 网络或上游暂不可用
    Dormant --> Dormant: 非唤醒语句丢弃
    Dormant --> Active: 句首识别“管家”
    Active --> Speaking: 收到 response.audio.delta
    Speaking --> Active: 播报完成
    Speaking --> Active: 用户开口打断
    Active --> Muted: 点击静音
    Muted --> Active: 取消静音
    Active --> Reconnecting: 连接中断
    Active --> Dormant: 明确退下/结束语且固定回应完成
    Reconnecting --> Dormant: 恢复成功
    Reconnecting --> Failed: 超出重试策略
    Active --> Closed: 用户结束
    Muted --> Closed: 用户结束
    Failed --> Idle: 用户重新开始
    Closed --> Idle: 新建语音对话
~~~

数据库字段 <code>ai_voice_session.status</code> 使用 connecting、active、closed、expired、failed；UI 的“播报、静音、重连”属于活动会话内部状态。

---

## 8. UML 领域类图

~~~mermaid
classDiagram
    class User {
        +Long userId
        +String userName
        +String nickName
        +String status
    }

    class VoiceSession {
        +String sessionId
        +Long userId
        +String modelName
        +String voiceName
        +String status
        +DateTime startedAt
        +DateTime endedAt
        +Long durationMs
        +Int messageCount
    }

    class VoiceMessage {
        +Long messageId
        +String sessionId
        +Int sequenceNo
        +String role
        +Text content
        +DateTime createTime
    }

    class UserMemory {
        +Long memoryId
        +Long userId
        +String memoryKey
        +String category
        +Text memoryValue
        +Decimal confidence
        +String status
        +DateTime lastUsedAt
    }

    class RealtimeGateway {
        +authenticate(token)
        +connectUpstream()
        +appendAudio(chunk)
        +forwardEvent(event)
        +close(reason)
    }

    class MemoryService {
        +loadForUser(userId)
        +extract(transcripts)
        +merge(memories)
        +delete(memoryId)
    }

    User "1" --> "0..*" VoiceSession : owns
    VoiceSession "1" --> "0..*" VoiceMessage : contains
    User "1" --> "0..*" UserMemory : remembers
    VoiceSession "0..1" --> "0..*" UserMemory : source
    RealtimeGateway ..> VoiceSession : persists
    RealtimeGateway ..> MemoryService : injects
    MemoryService ..> UserMemory : manages
~~~

---

## 9. ER 图与数据设计

### 9.1 核心 ER 图

~~~mermaid
erDiagram
    SYS_DEPT ||--o{ SYS_USER : "dept_id"
    SYS_USER ||--o{ SYS_USER_ROLE : "user_id"
    SYS_ROLE ||--o{ SYS_USER_ROLE : "role_id"
    SYS_ROLE ||--o{ SYS_ROLE_MENU : "role_id"
    SYS_MENU ||--o{ SYS_ROLE_MENU : "menu_id"
    SYS_USER ||--o{ SYS_USER_POST : "user_id"
    SYS_POST ||--o{ SYS_USER_POST : "post_id"

    SYS_USER ||--o{ AI_VOICE_SESSION : "user_id"
    AI_VOICE_SESSION ||--o{ AI_VOICE_MESSAGE : "session_id"
    SYS_USER ||--o{ AI_USER_MEMORY : "user_id"
    AI_VOICE_SESSION o|--o{ AI_USER_MEMORY : "source_session_id"

    SYS_USER {
        bigint user_id PK
        bigint dept_id
        varchar user_name UK
        varchar nick_name
        varchar password
        char status
        datetime login_date
    }

    SYS_ROLE {
        bigint role_id PK
        varchar role_name
        varchar role_key
        char status
    }

    SYS_MENU {
        bigint menu_id PK
        bigint parent_id
        varchar menu_name
        varchar perms
        char menu_type
    }

    SYS_DEPT {
        bigint dept_id PK
        bigint parent_id
        varchar dept_name
        char status
    }

    SYS_POST {
        bigint post_id PK
        varchar post_code
        varchar post_name
        char status
    }

    SYS_USER_ROLE {
        bigint user_id PK
        bigint role_id PK
    }

    SYS_ROLE_MENU {
        bigint role_id PK
        bigint menu_id PK
    }

    SYS_USER_POST {
        bigint user_id PK
        bigint post_id PK
    }

    AI_VOICE_SESSION {
        varchar session_id PK
        varchar qwen_session_id UK
        varchar user_key
        bigint user_id
        varchar client_id
        varchar client_ip
        varchar model_name
        varchar voice_name
        varchar status
        datetime started_at
        datetime ended_at
        bigint duration_ms
        int message_count
        varchar close_reason
    }

    AI_VOICE_MESSAGE {
        bigint message_id PK
        varchar session_id
        int sequence_no
        varchar role
        text content
        varchar qwen_item_id
        datetime create_time
    }

    AI_USER_MEMORY {
        bigint memory_id PK
        bigint user_id
        varchar memory_key
        varchar category
        text memory_value
        decimal confidence
        varchar source_session_id
        varchar status
        datetime last_used_at
        datetime create_time
        datetime update_time
    }
~~~

### 9.2 核心表说明

| 表 | 用途 | 关键约束 |
| --- | --- | --- |
| ai_voice_session | 一次实时语音连接的元数据、状态和质量统计 | session_id 主键；qwen_session_id 唯一 |
| ai_voice_message | 可选的语音转写消息 | session_id + sequence_no 唯一；不存原始音频 |
| ai_user_memory | 跨会话长期记忆 | user_id + memory_key 唯一；按账号隔离 |
| sys_user | 消费者与后台账号 | user_name 唯一 |
| sys_role / sys_menu | RBAC 角色、菜单和接口权限 | 通过关联表授权 |
| sys_logininfor | 登录审计 | 保存登录结果与来源 |
| sys_oper_log | 后台操作审计 | 保存敏感管理操作 |
| sys_config | 平台参数 | Java 服务动态配置 |

当前 SQL 延续 RuoYi 的约定，部分关系由应用逻辑和索引保证而非物理外键。修改或清理账号数据时，应通过服务层完成，避免产生孤立会话或记忆。

### 9.3 数据库脚本

- <code>sql/ry-cat.sql</code>：v1.0.0 全量初始化脚本。
- <code>sql/tmall-smart-home-assistant-upgrade.sql</code>：旧 RuoYi 库升级脚本。

全新环境只导入全量脚本；已有环境先备份再执行升级脚本。生产密码必须通过部署配置注入，禁止沿用示例密码。

---

## 10. 技术栈

| 层级 | 技术 | 当前版本/说明 |
| --- | --- | --- |
| 消费者端 | uni-app、Vue 3、Android Studio WebView 容器 | H5 与 Android 正式 APK；原生 `addJavascriptInterface` 桥 |
| T10S 本机控制 | Android `ContentResolver`、天猫精灵导出 Provider | `GenieApi`，文字识别方法 `15`；仅低风险白名单 |
| 浏览器音频 | Web Audio API、WebSocket | PCM 16-bit 单声道；输入 16kHz，输出 24kHz |
| 运营后台 | Vue 3、Vite、Element Plus、Pinia、Axios、ECharts | Vue 3.5.26、Vite 6.4.3、Element Plus 2.13.1 |
| Java 服务 | Java、Spring Boot、Spring Security、MyBatis、Druid | Java 17、Spring Boot 4.0.6、MyBatis Starter 4.0.1 |
| AI 网关 | Python、FastAPI、Uvicorn、websockets、httpx、aiomysql | 推荐 Python 3.11/3.12；Docker 使用 Python 3.11；FastAPI 0.115+ |
| 智能家居 Agent | LangGraph StateGraph、Pydantic、Qwen Function Calling | 单总控 + 有界工具；天气实时数据 + 模拟照度；确定性安全校验 |
| 实时模型 | Qwen3.5 Omni Realtime | qwen3.5-omni-plus-realtime，默认音色 Ethan |
| 文字模型 | Qwen / DeepSeek | 6 个可配置模型 |
| 记忆提取 | 阿里云百炼兼容接口 | 默认 qwen-plus |
| 数据库 | MySQL | 8.0+，默认库名 ry-cat |
| 缓存 | Redis | 6.0+，保存 Token 和认证相关缓存 |
| 反向代理 | Caddy 2 | 单域名入口、自动 HTTPS/WSS、静态资源与反向代理 |
| 测试 | JUnit/Maven、pytest | FastAPI 已有 auth/config/history/memory/realtime/text_chat 测试 |

### 10.1 文字模型映射

| 界面名称 | 服务端模型 ID |
| --- | --- |
| Qwen3.8-Max | qwen3.8-max |
| Qwen3.7-Plus | qwen3.7-plus-2026-05-26 |
| Qwen3.7-Flash | qwen3.7-flash-2026-07-15 |
| DeepSeek-V4-Pro | deepseek-v4-pro |
| DeepSeek-V4-Flash | deepseek-v4-flash-0731 |
| DeepSeek-R1 | deepseek-r1-0528 |

模型是否可用取决于百炼账号、地域、Workspace 和模型授权；源码中的模型 ID 可通过环境变量覆盖。

---

## 11. 仓库结构

~~~text
RuoYi/
├─ README.md                         # 当前软件工程总说明
├─ pom.xml                           # Java 聚合工程
├─ ruoyi-admin/                      # Java 启动模块、登录和运营 API
├─ ruoyi-framework/                  # Spring Security、Web 与基础配置
├─ ruoyi-system/                     # 用户、权限、语音会话和记忆领域服务
├─ ruoyi-common/                     # 通用组件
├─ ruoyi-fastapi/                    # AI 网关，一条 main.py 命令启动
│  ├─ main.py
│  ├─ assistant_server/
│  ├─ tests/
│  ├─ requirements.txt
│  └─ .env.example
├─ ruoyi-app/                        # uni-app 消费者端
│  ├─ pages/index.vue                # 实时语音首页
│  ├─ pages/text-chat.vue            # 文字对话
│  ├─ pages/login.vue
│  ├─ pages/register.vue
│  ├─ pages/common/agreement/        # 本地协议与政策
│  └─ android-native/                # 原生 WebView、GenieBridge 与 ContentProvider 适配
├─ ruoyi-ui/                         # Vue 3 运营后台
├─ ruoyi-docker/                     # Docker Compose 生产部署包
│  ├─ compose.yaml
│  ├─ config/
│  ├─ dockerfiles/
│  └─ scripts/
├─ docs/                             # 品牌图标等正式文档资源
└─ sql/
   ├─ ry-cat.sql
   └─ tmall-smart-home-assistant-upgrade.sql
~~~

已从聚合构建移除 <code>ruoyi-generator</code> 和 <code>ruoyi-quartz</code>；数据库也不再包含 gen_*、qrtz_* 和无业务用途的演示表。

---

## 12. 核心接口

### 12.1 Java 账号与运营接口（默认 8080）

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | /captchaImage | 登录验证码 |
| POST | /login | 登录并签发 Token |
| POST | /register | 注册消费者账号 |
| GET | /getInfo | 获取当前登录账号，FastAPI 也用它校验 Token |
| GET | /getRouters | 获取后台权限菜单 |
| GET | /assistant/overview | 运营概览 |
| GET | /assistant/session/list | 分页查询语音会话 |
| GET | /assistant/memory/list | 分页查询长期记忆 |
| DELETE | /assistant/memory/{memoryIds} | 删除长期记忆 |

除验证码、登录和按配置开放的注册接口外，其他接口均需要 Bearer Token；后台接口还需要对应 RBAC 权限。

### 12.2 FastAPI AI 网关（默认 8001）

| 类型 | 路径 | 用途 |
| --- | --- | --- |
| GET | / | 服务信息 |
| GET | /health/live | 进程存活检查 |
| GET | /health/ready | 配置、数据库和服务就绪检查 |
| GET | /metrics | Prometheus 文本指标（生产容器内网访问，不经公网网关暴露） |
| WS | /ws/v1/assistant | Qwen3.5 Omni 实时双向语音 |
| WS | /ws/v1/text-chat | 多模型流式文字对话 |
| GET | /api/v1/text-models | 获取可选文字模型 |
| GET | /api/v1/memories | 查询当前账号长期记忆 |
| DELETE | /api/v1/memories/{memory_id} | 删除当前账号单条记忆 |
| DELETE | /api/v1/memories | 清空当前账号记忆 |
| GET | /api/v1/agent/capabilities | 获取家庭 Agent 能力和状态时效配置 |
| POST | /api/v1/agent/plan | 根据语句、状态与偏好生成有界执行计划 |
| PUT | /api/v1/agent/household-state/{room} | 传感器/网关增量刷新指定房间实时状态 |
| GET | /api/v1/agent/household-state?room=客厅 | 查询当前账号指定房间状态及新鲜度 |
| DELETE | /api/v1/agent/household-state?room=客厅 | 清除指定房间或当前账号全部实时状态 |

Home Assistant、MQTT 网关或硬件采集服务可按 30～60 秒一次的频率增量刷新状态。例如：

```http
PUT /api/v1/agent/household-state/客厅
Authorization: Bearer <RuoYi 登录令牌>
Content-Type: application/json

{
  "indoor_temperature_c": 28.0,
  "indoor_humidity_percent": 68.0,
  "indoor_illuminance_lux": 120.0,
  "occupancy": true,
  "device_states": {
    "空调": { "power": false, "mode": "制冷", "temperature_c": 25 },
    "主灯": { "power": true, "brightness_percent": 35 }
  },
  "source": "home-assistant"
}
```

接口支持增量更新：温湿度传感器和设备网关可以分别写入，服务端会合并成同一房间快照。超过 TTL 未刷新后状态会标记为过期，Agent 不会继续把旧值当成实时事实。家居决策的最终回复下方会显示“本次参考”卡片，保存室温、湿度、天气、设备状态、时间段和偏好等可审计依据。

消费者端不直接连接阿里云百炼，也不能读取服务端 API Key。

---

## 13. 本地开发与启动

### 13.1 环境要求

- JDK 17
- Maven 3.9+
- MySQL 8.0+
- Redis 6.0+
- Python 3.11 或 3.12（推荐；当前 LangChain Core 暂不建议 Python 3.14）
- Node.js 20+ 与 npm
- HBuilderX 5.23 或兼容版本

### 13.2 初始化 MySQL

1. 创建数据库 <code>ry-cat</code>，字符集使用 <code>utf8mb4</code>。
2. 新环境导入 <code>sql/ry-cat.sql</code>。
3. 检查 <code>ruoyi-admin/src/main/resources/application-druid.yml</code> 的数据库连接。
4. 启动 Redis，并检查 Java 的 Redis 配置。

### 13.3 启动 Java 服务

~~~powershell
cd E:\无锡捷普迅智能科技有限公司\天猫精灵\天猫精灵安卓APK\RuoYi
mvn -pl ruoyi-admin -am spring-boot:run -DskipTests
~~~

默认地址：<code>http://127.0.0.1:8080</code>

### 13.4 启动 FastAPI AI 网关

~~~powershell
cd E:\无锡捷普迅智能科技有限公司\天猫精灵\天猫精灵安卓APK\RuoYi\ruoyi-fastapi
Copy-Item .env.example .env
python -m pip install -r requirements.txt
python main.py
~~~

在 <code>.env</code> 中填写有效的 <code>DASHSCOPE_API_KEY</code>。不要把真实 Key 写进 README、提交到 Git 或打包进客户端。

默认地址：<code>http://127.0.0.1:8001</code>

若 Windows 报 <code>WinError 10013</code>，说明端口被系统保留、策略禁止或已被占用。保留 Java 的 8080，将 FastAPI <code>PORT</code> 改为可用端口，并同步修改 <code>ruoyi-app/config.js</code> 或生产代理配置。

### 13.5 启动消费者端 H5

1. 用 HBuilderX 打开 <code>ruoyi-app</code>。
2. 选择“运行到浏览器 → Chrome”。
3. 默认 H5 地址为 <code>http://localhost:9090</code>。
4. 首次进入允许麦克风权限。

Chrome 在非 localhost 环境通常要求 HTTPS 才允许麦克风。工控屏或真机联调应使用 HTTPS/WSS，不能把电脑的 <code>127.0.0.1</code> 当作服务器地址。

### 13.6 启动运营后台

~~~powershell
cd E:\无锡捷普迅智能科技有限公司\天猫精灵\天猫精灵安卓APK\RuoYi\ruoyi-ui
npm install
npm run dev
~~~

默认地址：<code>http://localhost:9091</code>。Vite 已避开 Windows 常见的 80 端口权限问题。

### 13.7 推荐启动顺序

1. MySQL
2. Redis
3. Java 服务（8080）
4. FastAPI AI 网关（8001）
5. 消费者端 H5（9090）
6. 运营后台（9091）

### 13.8 Android v1.1.0 正式包

- 原生工程：`ruoyi-app/android-native`
- 应用包名：`com.jpx.tmallsmarthome`
- 最低系统：Android 6.0（API 23）
- 已验收设备：天猫精灵智慧屏 T10S，Android 10、1280×800 横屏、arm64-v8a
- 正式安装包：`ruoyi-app/apk/天猫智家语音助手-v1.1.0.apk`
- 拉起方式：Launcher Activity 或 `smartbutler://voice`

签名密钥位于本机忽略目录，不进入 Git、Docker 构建上下文或云服务器。重新构建时使用 Android Studio 自带 JBR 和 `D:\Android-SDK`。当前仓库未提交 Gradle Wrapper，需从 Android Studio 执行 Gradle 任务，或使用本机兼容的 Gradle 9.6.1 运行 `clean assembleRelease`；后续建议补交 Wrapper 以固定构建版本。

Android 原生容器在可信的 `file:///android_asset/` 页面注册 `GenieBridge`。桥接调用链是 `sendToGenie()` → `ContentResolver.insert()`，并在原生层再次校验低风险设备和操作。不要把开发调试用的 `adb shell content insert` 拼进 App，也不要申请 root 或 Shell 权限。

### 13.9 Docker Compose 一体化部署

生产容器相关文件已集中到 `ruoyi-docker`，不再散落在工程根目录和旧部署目录。首次部署时复制环境变量模板并运行统一脚本：

```bash
cp ruoyi-docker/.env.example ruoyi-docker/.env
vi ruoyi-docker/.env
sh ruoyi-docker/scripts/deploy.sh
```

编排包含 MySQL、Redis、Java API、FastAPI AI 网关和 Caddy Web 网关。详细目录、手动管理与安全说明见 [`ruoyi-docker/README.md`](ruoyi-docker/README.md)。工程根目录的 `.dockerignore` 是整个构建上下文的排除规则，仍需保留。

---

## 14. 配置说明

### 14.1 消费者端

部署人员在 <code>ruoyi-app/config.js</code> 配置：

- <code>baseUrl</code>：Java API 地址。
- <code>assistant.baseUrl</code>：FastAPI AI 网关地址。
- <code>appInfo.version</code>：当前产品版本，v1.1.0。

这些值在消费者界面中不提供编辑入口。

### 14.2 FastAPI

完整模板位于 <code>ruoyi-fastapi/.env.example</code>。关键变量：

| 变量 | 用途 | 默认/建议 |
| --- | --- | --- |
| DASHSCOPE_API_KEY | 百炼 API Key | 必填，仅服务端保存 |
| DASHSCOPE_REALTIME_URL | 实时语音 WSS | 按百炼地域/Workspace 配置 |
| DASHSCOPE_MODEL | 实时语音模型 | qwen3.5-omni-plus-realtime |
| DASHSCOPE_VOICE | 音色 | Ethan |
| GENIE_PROVIDER_ENABLED | 是否允许向声明本机能力的 Android 客户端下发家居指令事件 | true；非 T10S 客户端仍按能力协商关闭 |
| ACOUSTIC_RELAY_ENABLED | 是否启用外部天猫精灵声学转发回退 | false；仅在 Provider 不可用且明确需要声学方案时开启 |
| ACOUSTIC_RELAY_WAKE_PHRASE | 转发给外部设备的唤醒词 | 天猫精灵 |
| HOST / PORT | 监听地址和端口 | 0.0.0.0 / 8001 |
| ALLOWED_ORIGINS | 浏览器 CORS 白名单 | 生产环境填写明确域名；Android WebView 的空/`file://` Origin 由原生客户端规则处理 |
| MAX_CONNECTIONS | 每 Worker 最大连接 | 300 |
| MAX_CONNECTIONS_PER_USER | 单账号并发连接 | 3 |
| RUOYI_AUTH_URL | Token 校验地址 | http://127.0.0.1:8080/getInfo |
| DATABASE_ENABLED | 会话持久化 | true |
| VOICE_STORE_TRANSCRIPTS | 服务端保存转写 | false |
| MEMORY_ENABLED | 跨会话记忆 | true |
| TEXT_CHAT_ENABLED | 文字对话 | true |
| AGENT_HOUSEHOLD_STATE_TTL_SECONDS | 家庭实时状态有效期 | 300 秒 |
| AGENT_DEFAULT_ROOM | 隐式舒适诉求默认房间 | 客厅 |
| AGENT_STATE_REDIS_HOST / PORT / PASSWORD / DB | 多 Worker 共享家庭状态 | Docker 使用 redis:6379、DB 1；本地留空则使用内存 |

### 14.3 Android 拉起

应用清单已预留 URL Scheme：

~~~text
smartbutler://voice
~~~

天猫精灵技能、系统启动器或硬件方需要把唤醒事件映射到正式 APK 包名或此 Scheme。仅有 H5 页面无法自行完成系统级常驻唤醒；该链路需在 APK、系统权限和天猫精灵平台中联合配置。

---

## 15. 高并发与解耦设计

- 活动语音连接保存在对应 FastAPI Worker 内存中，连接之间不共享音频缓冲。
- <code>MAX_CONNECTIONS</code> 和 <code>MAX_CONNECTIONS_PER_USER</code> 防止单进程或单账号耗尽资源。
- MySQL 会话写入使用有界异步队列和独立 Worker，避免数据库延迟阻塞音频转发。
- 记忆提取使用独立队列和 Worker，不阻塞用户关闭会话。
- Java 认证结果支持短时缓存，但 Token 的权威来源仍是 RuoYi。
- FastAPI 不依赖 Java 内部类；只通过 <code>/getInfo</code> 和共享的数据模型边界协作。
- Agent 已作为独立编排层接入，设备协议仍留在 Android 原生桥；Home Assistant 后续以工具适配器接入，不把设备协议写进音频代理核心。
- 温湿度、照度、占用和设备状态存放在带 TTL 的 Redis 短时状态中，不写入对话历史；多 Worker 读取一致，过期值不会作为实时事实参与决策。

生产扩容建议：

1. Caddy 终止 TLS，并为 <code>/ws/</code> 保持 WebSocket 长连接与足够的读写超时。
2. 使用多个 FastAPI Worker/实例横向扩容。
3. 根据 Worker 数重新核算 MySQL 连接池总量。
4. 依据百炼账号实时并发配额设置系统上限。
5. 对 429、上游超时、断线重连、慢客户端和队列积压建立告警。

---

## 16. 安全、隐私与合规

- 前端不得包含百炼 API Key、数据库密码或 Redis 密码。
- 生产环境强制使用 HTTPS/WSS，并限制 <code>ALLOWED_ORIGINS</code>。
- 默认不保存原始音频；产品当前也没有上传图片或附件的功能。
- <code>VOICE_STORE_TRANSCRIPTS=false</code> 时，服务端不保存逐句转写，只保留会话状态和统计。
- 本机记录按登录账号隔离；退出或切换账号不能看到其他账号的记录。
- 长期记忆按服务端 <code>user_id</code> 隔离，接口不能信任客户端自行提交的用户编号。
- 密码由 RuoYi 的安全机制处理，禁止在日志中打印密码、Token 或 API Key。
- 用户协议和隐私政策保存在消费者端本地页面，发布前应由公司法务复核主体名称、联系方式、数据保留期限、第三方模型服务说明和注销流程。
- 家居指令只向本机天猫精灵 Provider 提交必要的短文本；运行时不使用 ADB、终端、root 或无障碍服务。
- Provider 能力由 Android 客户端握手声明；服务端检测和原生桥白名单构成两层校验，高风险指令不下发也不提交。
- 当前接口没有设备状态回执，`accepted=true` 只代表本机调用已提交，不能作为设备执行成功凭据。
- AI 回答可能不准确，客户端保留必要的生成内容提示。

---

## 17. 测试与验收

### 17.1 自动化检查

~~~powershell
# Java
cd E:\无锡捷普迅智能科技有限公司\天猫精灵\天猫精灵安卓APK\RuoYi
mvn test

# FastAPI
cd ruoyi-fastapi
python -m pytest

# 运营后台
cd ..\ruoyi-ui
npm run build:prod
~~~

### 17.2 v1.0.0 手工验收清单

- [ ] 新账号可注册、登录并进入助手。
- [ ] 连续 30 天未打开应用后要求重新登录。
- [ ] 登录后语音助手自动连接，状态由“连接中”变为“在线待命”。
- [ ] 用户语音能被转写，助手回答能实时播报。
- [ ] 播报时用户开口能够打断。
- [ ] 静音、结束、新建语音对话工作正常。
- [ ] 网络短暂中断后能自动重连且不会重复创建异常会话。
- [ ] 新会话能读取同账号有效长期记忆。
- [ ] 切换账号后不能看到前一账号的本机记录或长期记忆。
- [ ] 文字对话模型切换、流式输出、停止生成和返回按钮正常。
- [ ] 运营后台能查看概览、语音会话和长期记忆。
- [ ] 用户协议、隐私政策可离线打开且无 RuoYi 外链。
- [ ] 服务端日志不出现 API Key、密码或完整 Token。
- [ ] H5 在目标工控屏分辨率下无溢出、错位和异常图标。
- [ ] T10S 主应用握手声明 `genie_provider=true`，明确的灯/空调低风险指令能提交给 GenieApi。
- [ ] H5 与普通 Android 设备不声明 Provider 能力，不收到本机控制事件。
- [ ] 含糊指令以及门锁、燃气、安防等高风险指令被拒绝，界面不谎报设备已完成操作。
- [ ] 向家庭状态接口写入客厅温湿度、照度和空调状态后，说“我有点热”会引用这些状态、室外天气、时间段与账号偏好，再给出并提交适宜参数。
- [ ] 停止刷新超过 TTL 后，Agent 不再把旧状态描述为实时传感器事实。

---

## 18. 后续路线

### v1.1.x：移动端与部署完善

- 完善 Android 前后台生命周期、系统返回键和网络状态提示。
- 将临时公网 IP/明文 WS 迁移到正式域名、HTTPS/WSS 和证书自动续期。
- 正式域名、Caddy 自动 HTTPS/WSS、日志轮转和监控告警。
- 记忆命中率、提取延迟和用户纠错机制优化。

### v1.2.x：Agent 与智能家居深化

- 在现有 LangGraph 单总控与 Function Calling 基线上接入 Home Assistant 工具适配器。
- 让 Home Assistant/硬件网关持续推送真实室内照度、温湿度、人体存在和设备状态，替换未接硬件环境下的模拟兜底值。
- 增加设备状态查询、执行结果闭环、幂等键、分级确认和复杂自动化场景。
- 评估将 Dify 用于知识库与非实时运营流程，但保持实时语音控制主链路独立。

### 长期方向

- 唤醒词前端低功耗检测或系统级唤醒。
- 多用户家庭空间、儿童模式和访客模式。
- 记忆可解释性、过期策略和导出/注销闭环。
- 多实例共享限流、集中指标和高可用部署。

---

## 19. 开发交接约定

1. 先阅读本 README，再阅读对应模块 README。
2. 产品品牌名称统一使用“天猫智家”；当前语音唤醒口令仅为“管家”，“天猫管家”“曼巴管家”“智能管家”为停用的旧口令。
3. 模型询问身份时如实回答模型名称；应用品牌与模型身份分离。
4. 任何真实密钥只放环境变量或密钥管理服务。
5. 修改数据库结构时同时更新全量 SQL、升级 SQL 和本 README 的 ER 图。
6. 修改接口时同步更新接口表和消费者端调用。
7. 修改产品版本时同步更新本 README、<code>ruoyi-app/config.js</code> 和发布说明。
8. 实时音频代理只负责识别并下发结构化低风险意图；Android Provider、Home Assistant 或其他设备协议必须留在独立适配层。
9. 提交前至少运行与改动相关的 Java、Python 或前端构建测试。
10. 不提交 node_modules、dist、日志、.env、IDE 配置或真实用户数据。

---

## 20. License 与第三方服务

本项目是面向公司业务的 RuoYi 派生工程。正式发布前，请由项目负责人确认：

- 上游 RuoYi 及各开源依赖许可证义务；
- 阿里云百炼模型服务条款、计费、地域和数据处理规则；
- 天猫精灵技能平台与 Android 终端的发布要求；
- 公司自有代码、品牌素材和隐私政策的授权范围。

---

## 21. 后端与 SQL 代码检查记录（2026-08-11）

> 对 Java 后端（ruoyi-admin / ruoyi-framework / ruoyi-system）与 `sql/` 的 medium 只读检查结论。仅作审查记录，未改动任何业务代码。修复前请再次评估影响。

### 21.1 严重

1. **JWT 令牌密钥为 RuoYi 公开默认值** —— `ruoyi-admin/src/main/resources/application.yml:100` `token.secret: abcdefghijklmnopqrstuvwxyz`，可被离线伪造 admin 身份令牌；`application.yml:102` `expireTime: 43200`（30 天滑动续期）放大风险。
2. **Druid 监控台匿名开放 + 弱口令** —— `ruoyi-framework/.../config/SecurityConfig.java:106` 将 `/druid/**` 设为 permitAll；`application-druid.yml:44-51` `allow` 白名单为空、控制台账号 `ruoyi/123456`。
3. **默认管理员口令仍是 admin123** —— `sql/ry-cat.sql:611-613` admin / operator 的 BCrypt 值均为 RuoYi 默认口令 `admin123` 的公开哈希。
4. **Druid wall 允许多语句执行** —— `application-druid.yml:59-61` `multi-statement-allow: true`，会放大任意潜在注入点的危害。

### 21.2 中等

5. **数据库与初始口令明文** —— `application-druid.yml:11` MySQL root `123456`；`sql/ry-cat.sql:107` `sys.user.initPassword=123456`。
6. **普通角色权限过大** —— `sql/ry-cat.sql:507-578` role_id=2（分配给 operator）绑定了 `1000-1048` 全套用户/角色/菜单/部门/字典/参数增删改导出权限，与 `sql/tmall-smart-home-assistant-upgrade.sql:40-42` 注释「仅查看语音会话与长期记忆」严重不符。
7. **演示遗留 TestController** —— `ruoyi-admin/.../controller/tool/TestController.java`（第 34-35 行硬编码 admin123），且 `application.yml:127-131` springdoc 分组仅扫描该演示包。属应删除的垃圾代码。
8. **Swagger 生产默认开启且匿名可访问** —— `application.yml:123-125` + `SecurityConfig.java:106`（`/swagger-ui/**`、`/v3/api-docs/**` permitAll）。
9. **CORS 允许任意来源** —— `ruoyi-framework/.../config/ResourcesConfig.java:57-70` `addAllowedOriginPattern("*")` + 全 header + 全 method。

### 21.3 轻微

10. `application.yml:37` 生产日志级别 `com.ruoyi: debug`，会打印 SQL 与参数。
11. `application.yml:67-70` devtools 热部署 `enabled: true`，且 `ruoyi-admin/pom.xml:21-25` 仍引入 spring-boot-devtools。
12. `sql/tmall-smart-home-assistant-upgrade.sql:34-38` 菜单 `ON DUPLICATE KEY UPDATE` 子句漏更新 `route_name` 列。

### 21.4 已确认正常（重点核对项）

- **三张 ai 表字段与 Python 端 INSERT/UPDATE 完全匹配**（`sql/ry-cat.sql:14-77`）：`ai_voice_session` 含 `user_agent`，`ai_voice_message` 有 `(session_id,sequence_no)` 唯一键，`ai_user_memory` 的 `uk_ai_user_memory_key(user_id,memory_key)` 唯一索引可支撑 `history.py` / `memory.py` 的 `ON DUPLICATE KEY UPDATE`；无字段缺失、无类型不匹配。
- **四个 `/assistant` 接口均真实存在且带 `@PreAuthorize`**：`ruoyi-admin/.../controller/assistant/AiAssistantController.java:30-61`（overview / session:list / memory:list / memory:remove）。
- `AiAssistantMapper.xml` 全部使用 `#{}` 参数绑定、无 `${}` 拼接注入、无 N+1（`LEFT JOIN sys_user` 一次查完）、分页走 PageHelper、无空实现。
- `pom.xml:153-158` 已移除 generator / quartz 模块，`sql/ry-cat.sql` 无 `gen_*` / `qrtz_*` 残留，语音助手菜单与权限标识齐全。
- `pom.xml:19,31` 的 `spring-boot 4.0.6` / `springdoc 3.0.3` 已通过 Maven 与 Docker 多阶段构建验证，可正常解析并完成构建；后续升级仍需配套回归测试。

---

## 22. v1.1.0 发布验收与后续优化记录

本节原始清单来自 v1.0.0 完成后的一次完整代码审查。v1.1.0 已在原有生产地址、Android 权限、隐私弹窗、图标/启动页、WebView Origin、签名、T10S 横屏和云端实时语音基础上，增加本机 ContentProvider 控制链路。未关闭的生产安全加固与体验项不影响内部测试 APK；正式公开发布前仍须完成生产域名/HTTPS、密钥轮换、法务复核和 v1.1.0 T10S 主链路验收。

优先级说明：

| 类别 | 含义 | 是否阻断打包 |
| --- | --- | --- |
| A 类 | APK 运行阻断，打出来也跑不通 | 是 |
| B 类 | 安全漏洞，公网发布前必须修复 | 是 |
| C 类 | 功能性缺陷，影响体验或稳定性 | 否 |
| D 类 | 遗留清理与生产配置收紧 | 否 |
| E 类 | 功能增强建议，可排入后续版本 | 否 |

修复每一条后，请勾选对应复选框，并同步更新本文档中受影响的章节（接口表、配置表、版本号、验收清单）。

### 22.1 A 类：APK 打包阻断

- [x] **A-01 服务地址仍指向本机回环地址（v1.0.0 已处理）**
  - 位置：`ruoyi-app/config.js:4`（`baseUrl`）、`ruoyi-app/config.js:7`（`assistant.baseUrl`）
  - 现象：两个地址都是 `http://127.0.0.1`。打进 APK 后 `127.0.0.1` 指的是手机自身，登录和语音链路全部无法连接。
  - 建议：替换为生产 HTTPS/WSS 域名。若过渡期确实需要走明文 HTTP/WS 联调，需在 `ruoyi-app/manifest.json` 的 `app-plus.distribute.android` 中增加 `"usesCleartextTraffic": true`，因为 Android 9 及以上默认禁止明文流量。

- [x] **A-02 WebSocket 的 Origin 校验会拒绝 APK 客户端（v1.0.0 已处理并经 T10S 验证）**
  - 位置：`ruoyi-fastapi/main.py:203-206`（`/ws/v1/assistant`）、`ruoyi-fastapi/main.py:234-237`（`/ws/v1/text-chat`）
  - 现象：文字对话在 App 端走 `uni.connectSocket`，那是原生 socket，**不会发送 `Origin` 请求头**；语音走 renderjs 中的 `new WebSocket`，在 WebView 里 `Origin` 是 `file://` 或空字符串。当前 `ALLOWED_ORIGINS=*` 掩盖了该问题，一旦生产按第 14.2 节建议改成域名白名单，APK 会立即收到 4403 而无法建连。
  - 建议：把"来源校验"和"身份校验"解耦。Origin 白名单只用于浏览器 H5；对空 Origin 或 `file://` 的原生客户端放行，仍然依赖 `client.hello` 中的 RuoYi Token 完成鉴权。可增加 `ALLOW_NATIVE_CLIENTS` 开关明确该行为。

- [x] **A-03 缺少 Android 运行时麦克风权限申请（v1.0.0 已处理）**
  - 位置：`ruoyi-app/manifest.json:28`（仅静态声明 `RECORD_AUDIO`）；全项目搜索不到 `plus.android.requestPermissions`
  - 现象：Android 6 及以上必须动态申请危险权限。当前代码从未申请，WebView 中的 `getUserMedia()` 会直接失败，用户只能看到 `index-voice-bridge.js:148` 抛出的"麦克风不可用"这一句模糊提示。
  - 建议：在 `pages/index.vue` 的 `startSession()` 之前，用条件编译 `#ifdef APP-PLUS` 调用 `plus.android.requestPermissions(['android.permission.RECORD_AUDIO'])`，并对用户拒绝、"不再询问"两种结果分别给出可操作的引导（后者需引导至系统设置页）。

- [ ] **A-04 文字对话页的语音能力在 APK 中必然失效，且会反复弹出错误提示**
  - 位置：`ruoyi-app/pages/text-chat.vue:262-268`（`SpeechRecognition`）、`329-332`（`speechSynthesis`）、`505`（`text.done` 后自动播报）
  - 现象：语音识别和语音播报使用的是浏览器 Web Speech API。uni-app 的 App 逻辑层没有 `window` 对象，Android System WebView 也不实现这两个接口。后果是麦克风按钮永远提示"当前浏览器不支持语音输入"；更严重的是 `handleTextEvent` 在收到 `text.done` 后会无条件调用 `speakText()`，**模型每回答完一句就弹出一次"当前浏览器不支持语音播报"**。
  - 建议：二选一。最小改动是用条件编译在 App 平台隐藏麦克风与播报按钮，并去掉自动播报；完整方案是 App 端改用原生能力——识别走 `uni.getRecorderManager()` 上传服务端 ASR，播报走 `plus.speech` 或原生 TTS。无论选哪种，都必须消除"每次回答后弹窗"这一行为。

- [x] **A-05 缺少 Android 隐私政策弹窗与应用图标配置（v1.0.0 已处理）**
  - 位置：`ruoyi-app/` 下不存在 `androidPrivacy.json`；`ruoyi-app/manifest.json` 的 `app-plus.distribute` 中没有 `icons` 字段，也没有自定义启动图
  - 现象：中国大陆应用市场强制要求应用首次启动时弹出隐私政策并由用户确认；缺少图标配置会导致 APK 使用 HBuilderX 默认图标。
  - 建议：新增 `androidPrivacy.json`，其中的政策链接指向应用内的 `/pages/common/agreement/index`；在 `manifest.json` 中补齐各分辨率 `icons` 与启动图；同时确认 `minSdkVersion`、`targetSdkVersion` 与 `abiFilters`。

- [x] **A-06 H5 模板是 webpack 时代的残留文件（v1.0.0 已处理并通过 Vite 构建）**
  - 位置：`ruoyi-app/manifest.json:63`（`h5.template` 指向 `static/index.html`）、`ruoyi-app/static/index.html`
  - 现象：该模板使用 `<%= htmlWebpackPlugin.options.title %>` 和 `<%= VUE_APP_INDEX_CSS_HASH %>` 这类 Vue CLI 占位符，并且缺少 `</body>` 闭合标签与入口 `<script>`。本项目是 Vue 3 + Vite（`vueVersion: 3`），构建 H5 时应使用根目录的 `index.html`。
  - 建议：移除 `manifest.json` 中的 `h5.template` 配置并删除 `static/index.html`，或将其改写为 Vite 兼容的模板。改完后跑一次 H5 构建确认标题和样式正常。

### 22.2 B 类：安全

- [ ] **B-01 JWT 密钥仍是 RuoYi 公开默认值（最高危）**
  - 位置：`ruoyi-admin/src/main/resources/application.yml:100`
  - 现象：`token.secret` 为 `abcdefghijklmnopqrstuvwxyz`，这是 RuoYi 开源仓库中的默认值。任何人都能据此伪造合法 JWT 绕过登录；由于 FastAPI 网关完全信任 `/getInfo` 的返回结果（`ruoyi-fastapi/assistant_server/auth.py:44-59`），伪造的 Token 可以直接消耗百炼额度，并读取、删除任意账号的长期记忆。
  - 建议：改为足够长的随机值，并通过环境变量或密钥管理服务注入，禁止写死在配置文件中。密钥轮换后所有已签发 Token 失效，需在发布说明中提示用户重新登录。

- [ ] **B-02 Druid 监控台对外开放且使用弱口令**
  - 位置：`ruoyi-admin/src/main/resources/application-druid.yml:44-51`
  - 现象：`statViewServlet.enabled: true`、`allow` 为空（等同不限制来源 IP）、控制台账号为 `ruoyi/123456`。公网暴露会泄露 SQL 语句、表结构与数据源配置。
  - 建议：生产环境关闭 `statViewServlet`，或限制 `allow` 为内网网段并改用强口令。同时评估关闭 `filter.wall.config.multi-statement-allow`（第 61 行），它允许多语句执行，会放大注入影响面。

- [ ] **B-03 数据库口令硬编码进仓库**
  - 位置：`ruoyi-admin/src/main/resources/application-druid.yml:11`、`ruoyi-fastapi/.env.example:34`
  - 现象：MySQL `root` 账号密码 `123456` 直接写在配置文件中并随仓库分发。
  - 建议：改为占位符 + 环境变量注入；生产使用最小权限的专用数据库账号，而不是 `root`。（`ruoyi-fastapi/.env` 已确认未被 Git 跟踪，这点是正确的。）

- [ ] **B-04 指标接口无鉴权**
  - 位置：`ruoyi-fastapi/main.py:157-159`
  - 现象：`GET /metrics` 无需任何凭据即可访问，会泄露会话总量、容量拒绝次数、上游错误数等运营数据。
  - 建议：增加独立的采集令牌或限制为内网访问；同时评估 `/health/ready`（`main.py:119-154`）返回的内部状态是否需要一并收敛。

### 22.3 C 类：功能性缺陷

- [ ] **C-01 上游会话轮换会硬切麦克风**
  - 位置：`ruoyi-fastapi/assistant_server/realtime.py:339-348`；客户端对应 `ruoyi-app/pages/index-voice-bridge.js:78-89、201-207`
  - 现象：轮换时服务端发送 `assistant.session.rotating` 后立即结束连接，客户端 `onclose` 触发 `stopCapture()`，重连拿到 `assistant.session.ready` 后才重新 `getUserMedia()`。默认 `UPSTREAM_ROTATE_SECONDS=6900`，即每 115 分钟用户会听到一次明显中断，且该窗口内的语音全部丢失。
  - 建议：轮换期间保持本地采集不停止，仅暂存音频；或在服务端先建立新的上游连接再切换，实现对用户无感的续接。

- [ ] **C-02 最近对话缓存只增不减，存在慢性内存泄漏**
  - 位置：`ruoyi-fastapi/assistant_server/memory.py:67`（`_recent` 定义）、`212-231`（`_merge_recent`）
  - 现象：每个用户在 `_recent` 中常驻最多 24 条、单条最长 4000 字符的消息，过期判断只发生在该用户下一次调用 `get_context()` 时。不活跃用户的条目永远不会被回收，没有任何定期清扫机制。用户量大且进程长期运行时内存会持续增长。
  - 建议：增加后台定期清扫任务，或改用带容量上限的 LRU 结构。

- [ ] **C-03 关闭记忆开关后删除接口返回 500**
  - 位置：`ruoyi-fastapi/assistant_server/memory.py:144-162`（`delete_memory`、`clear_memories`），入口在 `ruoyi-fastapi/main.py:178-191`
  - 现象：这两个方法没有像 `list_memories` 那样先判断 `self.ready`，而是直接调用 `database.execute_now()`。当 `MEMORY_ENABLED=false` 时会抛出 `RuntimeError("数据库服务尚未就绪")`，客户端收到 500 而不是明确的功能未启用提示。
  - 建议：与 `list_memories` 保持一致，先判断 `self.ready`，未启用时返回明确的业务错误。

- [ ] **C-04 客户端断开被误判为上游初始化失败**
  - 位置：`ruoyi-fastapi/assistant_server/realtime.py:365-379`
  - 现象：`ClientWriter.run()`（`realtime.py:198-205`）在客户端已断开时调用 `send_text()` 抛出的是 `RuntimeError`，而该异常被归入"上游初始化失败"分支，导致日志、`ai_voice_session.close_reason` 与推送给客户端的错误码全部记录错误原因。
  - 建议：在 `ClientWriter` 内部捕获发送异常并转换为 `SlowClientError` 或独立的客户端断开异常，使其走 `realtime.py:380-383` 的正常关闭分支。

- [ ] **C-05 登录成功后获取用户信息失败会卡死在登录页**
  - 位置：`ruoyi-app/pages/login.vue:121-126`
  - 现象：`loginSuccess()` 中 `useUserStore().getInfo().then(...)` 没有 `.catch` 分支。此时 loading 已经关闭、Token 已写入本地，若 `/getInfo` 失败则页面没有任何反馈，用户点击登录后看起来毫无反应。
  - 建议：补充 `.catch`，给出明确提示；并考虑在 Token 已写入的情况下允许直接进入助手页，由 `App.vue` 的滑动续期逻辑后续补齐用户信息。

- [ ] **C-06 注册入口写死为始终显示**
  - 位置：`ruoyi-app/pages/login.vue:58`
  - 现象：`const register = ref(true)` 是硬编码值，没有读取服务端的 `sys.account.registerUser` 配置。当服务端关闭注册时，用户仍能看到"立即注册"，点进去填完表单才会被拒绝。
  - 建议：由服务端下发注册开关，前端据此控制入口显隐。

### 22.4 D 类：清理与生产配置

- [ ] **D-01 消费者端残留大量 RuoYi 模板代码**
  - 位置：`ruoyi-app/pages/mine/`（7 个文件）、`ruoyi-app/pages/work/index.vue`、`ruoyi-app/pages/common/textview/`、`ruoyi-app/components/uni-section/`、`ruoyi-app/api/system/dict/`、`ruoyi-app/plugins/tab.js`、`ruoyi-app/plugins/auth.js`、`ruoyi-app/utils/dict.js`、`ruoyi-app/utils/permission.js`、`ruoyi-app/utils/upload.js`、`ruoyi-app/store/modules/dict.js`
  - 现象：这些文件既未在 `pages.json` 中注册，也没有被任何在用页面引用，属于纯遗留代码，会干扰后续维护者判断功能边界。
  - 建议：确认无引用后删除，并同步精简 `main.js` 中对 `useDict` 与 `plugins` 的注册。

- [ ] **D-02 静态目录中约 350 KB 无用资源会原样打进 APK**
  - 位置：`ruoyi-app/static/scss/colorui.css`（136 KB）、`ruoyi-app/static/images/banner/`（3 张，约 115 KB）、`ruoyi-app/static/images/profile.jpg`（81 KB）、`ruoyi-app/static/images/tabbar/`（6 张，约 24 KB）、`ruoyi-app/static/logo200.png`
  - 现象：`static/` 目录在打包时整包拷贝，不参与 tree-shaking，未被引用的资源同样会进入安装包。
  - 建议：删除确认无引用的资源。注意 `store/modules/user.js:9` 仍引用 `profile.jpg` 作为默认头像，删除前需一并处理。

- [ ] **D-03 已移除模块的空目录仍然存在**
  - 位置：`RuoYi/ruoyi-generator/`、`RuoYi/ruoyi-quartz/`
  - 现象：`pom.xml` 的 `<modules>` 中已移除这两个模块，目录内也不再包含 Java 源码，但目录本身仍留在仓库里，容易让接手者误以为模块仍在使用。
  - 建议：两个目录已不参与构建，确认不再需要保留目录占位后可直接删除；原临时归档目录已于 2026 年 8 月 12 日完成清理。

- [ ] **D-04 生产配置未收紧**
  - 位置：`ruoyi-admin/src/main/resources/application.yml`
  - 现象：
    - 第 10 行 `profile: D:/tmall-smart-home/uploadPath` 是 Windows 绝对路径，Linux 部署会直接失败；
    - 第 37 行 `com.ruoyi: debug` 会打印 SQL 与参数；
    - 第 67-70 行 `devtools.restart.enabled: true` 不应用于生产；
    - 第 124 行 `swagger-ui.enabled: true`，且第 131 行 `packages-to-scan` 指向已删除的 `com.ruoyi.web.controller.tool` 包；
    - 第 138 行 `referer.allowed-domains` 仍是 `ruoyi.vip`；
    - 第 147 行 `xss.urlPatterns` 未覆盖 `/assistant/*`。
  - 建议：拆分出生产 profile，逐项按环境覆盖。

- [ ] **D-05 隐私政策缺少个人信息处理者主体信息**
  - 位置：`ruoyi-app/pages/common/agreement/index.vue:35`
  - 现象：联系方式一段只写了"请通过产品说明、应用安装渠道或服务合同中公布的运营方联系方式与我们联系"，没有列明公司全称与具体联系方式。国内应用市场审核通常要求隐私政策明确写出个人信息处理者名称和有效联系渠道。
  - 建议：补充"无锡捷普迅智能科技有限公司"全称、办公地址与联系邮箱，并按第 16 节要求由法务复核数据保留期限、第三方模型服务说明与账号注销流程。

### 22.5 E 类：功能增强建议

以下为纯语音助手范围内的体验改进，不涉及 Agent 与家居控制，可按排期纳入 v1.1.x。

- [ ] **E-01 真实输入电平指示**：`ruoyi-app/pages/index.vue:218-221` 的 `voice-bars` 目前只是 CSS 动画，与实际音量无关。可在 `index-voice-bridge.js` 的采集链路上接入 `AnalyserNode`，把真实电平回传给页面，让用户确认麦克风确实在工作。
- [ ] **E-02 重连兜底终止态**：`ruoyi-app/pages/index-voice-bridge.js:94-107` 目前是无限指数退避，最长间隔 15 秒。用户在服务不可用时会永远看到"正在恢复连接"。建议连续失败达到阈值后进入明确的失败态，提示检查网络并提供手动重试入口。
- [ ] **E-03 网络状态监听**：接入 `uni.onNetworkStatusChange`，断网时直接给出"网络已断开"，而不是让用户对着重连提示等待。
- [ ] **E-04 长期记忆支持纠错**：`ruoyi-app/pages/index.vue` 的管家记忆页目前只能删除。若模型提取出不准确的事实，用户只能整条删掉。建议增加编辑能力，对应服务端补充更新接口。
- [ ] **E-05 Android 返回键二次确认**：语音主页未处理系统返回键，用户误触会直接退出应用并中断通话。建议在 App 平台增加二次确认或最小化行为。

### 22.6 处理约定

1. 每完成一条，勾选对应复选框并在提交信息中标注编号（例如 `A-03`）。
2. A 类与 B 类全部完成后，才能进入 HBuilderX 云打包流程。
3. 涉及接口或配置变更的条目，必须同步更新第 12 节接口表与第 14 节配置表。
4. 若某条目在实施中发现方案不成立，请在本节中记录结论与替代方案，不要静默跳过。
5. 本清单中的已完成能力已纳入 v1.1.0；新增或遗留事项完成后，应按语义化版本规则继续升级并同步第 1 节与验收清单。

---

**当前文档基线：天猫智家 v1.1.0 · 2026 年 8 月 13 日 13:07:54（UTC+8）**

**当前构建状态：v1.1.0 回声抑制与 ContentProvider 直连修复包、FastAPI、H5 与 Docker 配置已验证；待在 T10S 安装本次 APK 后复测主链路。**
