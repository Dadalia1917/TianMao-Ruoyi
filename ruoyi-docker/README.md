# 天猫智家 Docker 部署包

本目录集中保存天猫智家 v1.1.0 的容器编排、镜像构建和部署脚本。Docker 构建上下文仍为上一级 `RuoYi` 工程根目录，以便构建 Java、FastAPI、消费者端 H5 和运营后台。

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
