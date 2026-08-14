#!/usr/bin/env bash
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get install -y ca-certificates curl

install -m 0755 -d /etc/apt/keyrings

if curl --retry 3 --retry-delay 2 -fsSL \
  https://download.docker.com/linux/ubuntu/gpg \
  -o /etc/apt/keyrings/docker.asc; then
  chmod a+r /etc/apt/keyrings/docker.asc

  . /etc/os-release
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" \
    > /etc/apt/sources.list.d/docker.list

  apt-get update
  apt-get install -y \
    docker-ce \
    docker-ce-cli \
    containerd.io \
    docker-buildx-plugin \
    docker-compose-plugin
else
  # 中国大陆网络偶尔无法访问 download.docker.com；此时使用 Ubuntu
  # 软件仓库提供的 Docker Engine 和 Compose v2。
  rm -f /etc/apt/sources.list.d/docker.list
  apt-get update
  apt-get install -y docker.io docker-compose-v2
fi

systemctl enable --now docker
docker --version
docker compose version
