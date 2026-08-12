FROM node:22-alpine AS admin-builder

WORKDIR /build
COPY ruoyi-ui/package.json ruoyi-ui/package-lock.json ./
RUN npm config set registry https://registry.npmmirror.com \
    && npm config set replace-registry-host always \
    && npm config set fetch-retries 5 \
    && npm config set fetch-timeout 120000 \
    && npm ci --no-audit
COPY ruoyi-ui/ ./
RUN npm run build:prod

FROM node:20-alpine AS app-builder

WORKDIR /build
COPY ruoyi-app/package.json ruoyi-app/package-lock.json ./
RUN npm config set registry https://registry.npmmirror.com \
    && npm config set replace-registry-host always \
    && npm config set fetch-retries 5 \
    && npm config set fetch-timeout 120000 \
    && npm ci --no-audit
COPY ruoyi-app/ ./
RUN npm run build:h5

FROM caddy:2-alpine

COPY deploy/docker/Caddyfile /etc/caddy/Caddyfile
COPY --from=admin-builder /build/dist /srv/admin
COPY --from=app-builder /build/dist /srv/app
COPY ruoyi-app/static/audio/pcm-capture-worklet.js /srv/app/static/audio/pcm-capture-worklet.js

EXPOSE 80 443 443/udp
