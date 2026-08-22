# 天猫智家 Docker 部署包

本目录对应天猫智家 v1.2.1 源码/文档基线，集中保存容器编排、镜像构建和部署脚本。文档更新时间为 2026.08.21（UTC+8）。Docker 构建上下文仍为上一级 `RuoYi` 工程根目录，以便构建 Java、FastAPI、消费者端 H5 和运营后台。

> v1.2.1 状态：FastAPI 已完成显式 Agent 分派，并将 `qwen3.8-max` 调整为关闭 thinking 的低延迟策略；本轮未构建或启动 Docker，也未部署正式服务器。下述 v1.1.2 镜像与云端信息是已验收历史基线，不能改标为 v1.2.1。

> 发布状态（2026.08.17）：本地 Compose 三项业务镜像标签已统一为 v1.1.2，AI 网关基础镜像从 `python:3.11-slim` 升级为官方 `python:3.14.6-slim`；依赖安装及 Linux 镜像构建成功，本机 YOLO Python 3.14.4 回归为 `110 passed`。

> 云端状态：正式 RuoYi `120.55.64.225:/opt/tmall-smart-home` 已同步 v1.1.2；`java-api`、`ai-gateway`、`web-gateway` 三项业务镜像已切换，FastAPI 实际运行 Python 3.14.6 且内部 `/health/ready` 全部 ready。云端只保留经包内版本核验的 `backups/rollback-v1.1.1-20260817-101501.tar.gz`；若出现 3.14 特有问题，可恢复该包并回滚 Python 3.11。`139.196.94.58:/opt/tmall-genie-ai` 是旧 DeepSeek Webhook，本轮未改动。

## 目录结构

```text
ruoyi-docker/
├─ compose.yaml                 # MySQL、Redis、Java、FastAPI、Caddy 编排
├─ .env.example                 # 本地开发配置说明，可提交
├─ .env                         # 已脱敏的团队本地默认值，可提交
├─ config/
│  ├─ Caddyfile                 # HTTPS、静态站点和反向代理
│  ├─ daemon.aliyun.json        # 可选的阿里云 Docker 镜像加速配置
│  └─ maven-settings.xml        # 容器内 Maven 镜像配置
├─ dockerfiles/
│  ├─ java.Dockerfile
│  ├─ fastapi.Dockerfile
│  └─ gateway.Dockerfile
└─ scripts/
   ├─ deploy.sh                 # 校验、构建并启动完整服务
   └─ install-docker-ubuntu.sh  # Ubuntu Docker 安装辅助脚本
```

工程根目录的 `.dockerignore` 必须保留；它用于控制发送给 Docker Builder 的整个 RuoYi 构建上下文。

## 本地开箱启动

仓库内 `.env` 已统一使用 MySQL `root / 123456`，Redis 本地密码为 `123456`。同事克隆后可直接执行：

```bash
docker compose -f ruoyi-docker/compose.yaml --env-file ruoyi-docker/.env up -d --build --wait
```

不填写 `DASHSCOPE_API_KEY` 也能构建和启动基础服务；实时语音、文字模型和 Agent 的外部调用需要在启动进程前通过系统环境变量注入真实 Key。仓库中的本地密码和 Token 只用于开发机，不得直接用于公网。

## 首次生产部署

在 Ubuntu 服务器的工程根目录执行：

```bash
cp ruoyi-docker/.env ruoyi-docker/.env.production.local
chmod 600 ruoyi-docker/.env.production.local
vi ruoyi-docker/.env.production.local
sh ruoyi-docker/scripts/deploy.sh ruoyi-docker/.env.production.local
```

必须替换 MySQL、Redis、Token、本地域名和百炼 API Key；`.env.production.local` 已被忽略。真实密码和 API Key 只能放在服务器私有环境文件或密钥服务，不得写入 `.env`、Compose、README、镜像或 Git。

## 手动管理

```bash
# 仅校验最终编排
docker compose -f ruoyi-docker/compose.yaml --env-file ruoyi-docker/.env config --quiet

# 构建并启动
docker compose -f ruoyi-docker/compose.yaml --env-file ruoyi-docker/.env up -d --build --wait

# 查看状态与日志
docker compose -f ruoyi-docker/compose.yaml --env-file ruoyi-docker/.env ps
docker compose -f ruoyi-docker/compose.yaml --env-file ruoyi-docker/.env logs -f --tail=200

# 停止服务但保留数据库卷
docker compose -f ruoyi-docker/compose.yaml --env-file ruoyi-docker/.env down
```

不要随意执行带 `-v` 的 `down`，否则会删除 MySQL、Redis 和业务数据卷。更新源码后重新执行 `sh ruoyi-docker/scripts/deploy.sh` 即可重建并滚动替换本机容器。

## 对外入口

- `/app/`：消费者端 H5
- `/admin/`：运营后台
- `/api/`：Java API
- `/assistant/`、`/ws/`：FastAPI 与 WebSocket

生产语音采集需要有效域名和 HTTPS/WSS。没有域名时的 `http://:80` 仅适合初期联调。

## 当前阿里云目录差异

现网是早期扁平部署，不是本地 `ruoyi-docker/` 布局。SSH 登录后使用以下真实路径：

```bash
cd /opt/tmall-smart-home
docker compose -f compose.yaml --env-file deploy/docker/.env ps
docker compose -f compose.yaml --env-file deploy/docker/.env logs -f --tail=200
curl -fsS http://127.0.0.1/health/ready
```

`/opt/tmall-smart-home/deploy/docker/.env` 权限为 600；当前唯一回滚包位于服务器 `backups/rollback-v1.1.1-20260817-101501.tar.gz`，包内 `APP_VERSION=1.1.1` 已核验。现网 Agent 使用 `qwen3.8-max`，家电仍由 T10S 天猫精灵内部 `GenieApi` 控制，不经过 Docker 或 Home Assistant。
