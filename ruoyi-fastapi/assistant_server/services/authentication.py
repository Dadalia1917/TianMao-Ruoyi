from __future__ import annotations

import asyncio
import hashlib
import time
from dataclasses import dataclass

import httpx

from ..core.config import Settings


class AuthenticationError(Exception):
    pass


@dataclass(slots=True)
class _CacheEntry:
    user_id: str
    expires_at: float


class RuoYiAuthenticator:
    """Validate the RuoYi token and resolve the account owning a voice session."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._cache: dict[str, _CacheEntry] = {}
        self._lock = asyncio.Lock()
        self._client = httpx.AsyncClient(timeout=5.0)

    async def authenticate(self, token: str | None) -> str:
        token = (token or "").strip()
        if not token:
            raise AuthenticationError("登录状态已失效，请重新登录")

        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        now = time.monotonic()
        async with self._lock:
            cached = self._cache.get(token_hash)
            if cached and cached.expires_at > now:
                return cached.user_id

        try:
            response = await self._client.get(
                self._settings.ruoyi_auth_url,
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise AuthenticationError("账号服务暂时不可用") from exc

        if payload.get("code", 200) != 200:
            raise AuthenticationError(payload.get("msg") or "登录状态已失效")
        user = payload.get("user") or {}
        user_id = str(user.get("userId") or "").strip()
        if not user_id:
            raise AuthenticationError("账号服务未返回有效用户")

        async with self._lock:
            self._cache[token_hash] = _CacheEntry(
                user_id=user_id,
                expires_at=now + self._settings.ruoyi_auth_cache_seconds,
            )
            if len(self._cache) > 10_000:
                self._cache = {
                    key: value for key, value in self._cache.items() if value.expires_at > now
                }
        return user_id

    async def close(self) -> None:
        await self._client.aclose()
