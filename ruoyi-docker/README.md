# 天猫智家 Docker 部署包

本目录集中保存天猫智家 v1.1.1 的容器编排、镜像构建和部署脚本。Docker 构建上下文仍为上一级 `RuoYi` 工程根目录，以便构建 Java、FastAPI、消费者端 H5 和运营后台。

> 发布状态（2026 年 8 月 14 日 20:04:17）：阿里云 `java-api`、`ai-gateway`、`web-gateway` 已更新为 v1.1.1 联动版，MySQL/Redis 数据卷保持不变；公网健康接口返回 v1.1.1/ready，Agent 对“我有点累了”实测生成待确认的音乐播放器方案。

> 语音部署验收：Compose 已透传 `REALTIME_VAD_*` 与 `REALTIME_ECHO_GUARD_SECONDS`；云端 H5 已包含 929 字节 `pcm-capture-worklet.js`，采集诊断、播报状态与回灌过滤代码已上线。

## 目录结构

```text
ruoyi-docker/
├─ compose.yaml                 # MySQL、Redis、Java、FastAPI、Caddy 编排
├─ .env.example                 # 生产环境变量模板，可提交
├─ .env                         # 本机/服务器密钥，不提交
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

## 首次部署

在 Ubuntu 服务器的工程根目录执行：

```bash
cp ruoyi-docker/.env.example ruoyi-docker/.env
chmod 600 ruoyi-docker/.env
vi ruoyi-docker/.env
sh ruoyi-docker/scripts/deploy.sh
```

至少替换 MySQL、Redis、Token、百炼 API Key 等 `CHANGE_ME` 项。真实密码和 API Key 只能放在 `ruoyi-docker/.env`，不得写入 Compose、README、镜像或 Git。

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

`/opt/tmall-smart-home/deploy/docker/.env` 权限为 600；部署前回滚包位于服务器 `backups/v1.1.1-before-20260814-194008.tar.gz`。现网 Agent 使用 `qwen3.8-max`，家电仍由 T10S 天猫精灵内部 `GenieApi` 控制，不经过 Docker 或 Home Assistant。
