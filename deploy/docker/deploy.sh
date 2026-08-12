#!/usr/bin/env sh
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
PROJECT_DIR="$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd)"
ENV_FILE="${1:-$PROJECT_DIR/deploy/docker/.env}"

cd "$PROJECT_DIR"

if [ ! -f "$ENV_FILE" ]; then
  echo "缺少 $ENV_FILE，请先复制 deploy/docker/.env.example 并填写生产配置。" >&2
  exit 1
fi

if grep -Eq '^[[:space:]]*(MYSQL_ROOT_PASSWORD|MYSQL_APP_PASSWORD|REDIS_PASSWORD|TOKEN_SECRET|DASHSCOPE_API_KEY)=.*CHANGE_ME' "$ENV_FILE"; then
  echo "$ENV_FILE 仍包含 CHANGE_ME 占位值，请先填写真实密钥和随机强密码。" >&2
  exit 1
fi

chmod 600 "$ENV_FILE" 2>/dev/null || true

docker compose --env-file "$ENV_FILE" config --quiet

# 2 vCPU / 8 GiB ECS 上串行构建，避免 Maven、两个 Node 构建同时抢占内存。
COMPOSE_PARALLEL_LIMIT="${COMPOSE_PARALLEL_LIMIT:-1}"
export COMPOSE_PARALLEL_LIMIT
COMPOSE_BAKE="${COMPOSE_BAKE:-false}"
export COMPOSE_BAKE

docker compose --env-file "$ENV_FILE" build --pull
docker compose --env-file "$ENV_FILE" up -d --remove-orphans --wait --wait-timeout 300
docker compose --env-file "$ENV_FILE" ps
