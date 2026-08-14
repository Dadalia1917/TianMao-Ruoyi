from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

from redis.asyncio import Redis
from redis.exceptions import RedisError, WatchError

from .schemas import HouseholdStateSnapshot, HouseholdStateUpdate

logger = logging.getLogger(__name__)


class HouseholdStateStore:
    """Concurrency-safe, short-lived household telemetry.

    This is intentionally operational state rather than conversation history.  A
    sensor gateway or Home Assistant should refresh it continuously; stale values
    are never presented to the agent as live facts.
    """

    def __init__(
        self,
        *,
        ttl_seconds: int = 300,
        redis_host: str = "",
        redis_port: int = 6379,
        redis_password: str = "",
        redis_db: int = 1,
    ) -> None:
        self.ttl_seconds = max(30, int(ttl_seconds))
        self.redis_host = redis_host.strip()
        self.redis_port = int(redis_port)
        self.redis_password = redis_password
        self.redis_db = int(redis_db)
        self._redis: Redis | None = None
        self._items: dict[tuple[str, str], dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    @property
    def backend(self) -> str:
        return "redis" if self._redis is not None else "memory"

    async def start(self) -> None:
        if not self.redis_host:
            logger.info("household state store using local memory")
            return
        client = Redis(
            host=self.redis_host,
            port=self.redis_port,
            password=self.redis_password or None,
            db=self.redis_db,
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=3,
            health_check_interval=30,
        )
        try:
            await client.ping()
        except RedisError:
            await client.aclose()
            logger.exception(
                "household state Redis unavailable; falling back to local memory"
            )
            return
        self._redis = client
        logger.info(
            "household state store using Redis: host=%s port=%s db=%s ttl=%ss",
            self.redis_host,
            self.redis_port,
            self.redis_db,
            self.ttl_seconds,
        )

    async def close(self) -> None:
        client, self._redis = self._redis, None
        if client is not None:
            await client.aclose()

    @staticmethod
    def _utc_now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _aware(value: datetime | None) -> datetime:
        value = value or HouseholdStateStore._utc_now()
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    async def update(
        self, user_id: str, room: str, update: HouseholdStateUpdate
    ) -> HouseholdStateSnapshot:
        key = (str(user_id), room.strip() or "客厅")
        received_at = self._utc_now()
        if self._redis is not None:
            return await self._update_redis(key, update, received_at)
        async with self._lock:
            previous = self._merge(self._items.get(key), update, received_at)
            self._items[key] = previous
            return self._snapshot(key, previous, received_at)

    async def get(self, user_id: str, room: str) -> HouseholdStateSnapshot | None:
        key = (str(user_id), room.strip() or "客厅")
        now = self._utc_now()
        if self._redis is not None:
            try:
                raw = await self._redis.get(self._redis_key(key))
            except RedisError:
                logger.exception("failed to read household state from Redis")
                raw = None
            return self._snapshot(key, self._decode(raw), now) if raw else None
        async with self._lock:
            item = self._items.get(key)
            return self._snapshot(key, item, now) if item else None

    async def clear(self, user_id: str, room: str | None = None) -> int:
        if self._redis is not None:
            try:
                if room:
                    return int(
                        await self._redis.delete(
                            self._redis_key((str(user_id), room.strip() or "客厅"))
                        )
                    )
                keys = [
                    key
                    async for key in self._redis.scan_iter(
                        match=f"tmall:household-state:{quote(str(user_id), safe='')}:*"
                    )
                ]
                return int(await self._redis.delete(*keys)) if keys else 0
            except RedisError:
                logger.exception("failed to clear household state from Redis")
                return 0
        async with self._lock:
            if room:
                return int(self._items.pop((str(user_id), room.strip()), None) is not None)
            keys = [key for key in self._items if key[0] == str(user_id)]
            for key in keys:
                self._items.pop(key, None)
            return len(keys)

    async def _update_redis(
        self,
        key: tuple[str, str],
        update: HouseholdStateUpdate,
        received_at: datetime,
    ) -> HouseholdStateSnapshot:
        assert self._redis is not None
        redis_key = self._redis_key(key)
        for _ in range(3):
            try:
                async with self._redis.pipeline(transaction=True) as pipe:
                    await pipe.watch(redis_key)
                    raw = await pipe.get(redis_key)
                    merged = self._merge(self._decode(raw), update, received_at)
                    pipe.multi()
                    pipe.set(
                        redis_key,
                        self._encode(merged),
                        ex=self.ttl_seconds,
                    )
                    await pipe.execute()
                    return self._snapshot(key, merged, received_at)
            except WatchError:
                continue
            except RedisError:
                logger.exception("failed to update household state in Redis")
                break
        raise RuntimeError("家庭状态更新冲突，请稍后重试")

    def _merge(
        self,
        current: dict[str, Any] | None,
        update: HouseholdStateUpdate,
        received_at: datetime,
    ) -> dict[str, Any]:
        merged = dict(current or {})
        incoming = update.model_dump(exclude_none=True)
        previous_devices = dict(merged.get("device_states") or {})
        for device, state in incoming.pop("device_states", {}).items():
            previous_devices[str(device)] = dict(state or {})
        merged.update(incoming)
        merged["device_states"] = previous_devices
        merged["observed_at"] = self._aware(update.observed_at)
        merged["received_at"] = received_at
        return merged

    @staticmethod
    def _redis_key(key: tuple[str, str]) -> str:
        return "tmall:household-state:%s:%s" % (
            quote(key[0], safe=""),
            quote(key[1], safe=""),
        )

    @staticmethod
    def _encode(item: dict[str, Any]) -> str:
        return json.dumps(
            item,
            ensure_ascii=False,
            separators=(",", ":"),
            default=lambda value: value.isoformat()
            if isinstance(value, datetime)
            else str(value),
        )

    @staticmethod
    def _decode(raw: str | None) -> dict[str, Any]:
        if not raw:
            return {}
        value = json.loads(raw)
        for field in ("observed_at", "received_at"):
            if value.get(field):
                value[field] = datetime.fromisoformat(value[field])
        return value

    def _snapshot(
        self,
        key: tuple[str, str],
        item: dict[str, Any],
        now: datetime,
    ) -> HouseholdStateSnapshot:
        observed_at = self._aware(item.get("observed_at"))
        age = max(0, int((now - observed_at).total_seconds()))
        return HouseholdStateSnapshot(
            user_id=key[0],
            room=key[1],
            indoor_temperature_c=item.get("indoor_temperature_c"),
            indoor_humidity_percent=item.get("indoor_humidity_percent"),
            illuminance_lux=item.get("illuminance_lux"),
            occupancy=item.get("occupancy"),
            device_states=dict(item.get("device_states") or {}),
            source=str(item.get("source") or "sensor_gateway"),
            observed_at=observed_at,
            received_at=self._aware(item.get("received_at")),
            fresh=age <= self.ttl_seconds,
            expires_in_seconds=max(0, self.ttl_seconds - age),
        )
