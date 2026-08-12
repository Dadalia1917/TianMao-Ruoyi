from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass
from typing import Any, Iterable

import httpx

from .config import Settings
from .history import VoiceHistoryStore

logger = logging.getLogger(__name__)

_ALLOWED_CATEGORIES = {
    "preference",
    "profile",
    "routine",
    "relationship",
    "goal",
    "other",
}
_SAFE_KEY = re.compile(r"[^a-z0-9._-]+")
_SENSITIVE_MEMORY = re.compile(
    r"密码|口令|验证码|api\s*key|access\s*token|refresh\s*token|密钥|"
    r"身份证|银行卡|信用卡|完整住址|精确住址",
    re.I,
)

_EXTRACTION_SYSTEM_PROMPT = """你是天猫智家的长期记忆整理器。请从对话中提取用户明确表达、未来仍有帮助的稳定事实。

仅保存：偏好、基础资料、长期习惯、重要人物关系、持续目标。不要保存一次性问题、临时状态、助手的推测或助手自己说的话。
绝不保存：密码、验证码、API Key、令牌、身份证号、银行卡号、精确住址、财务账户、完整医疗隐私，或用户未明确表达的敏感结论。
相同含义使用稳定、简短的小写英文 key；value 使用简洁中文第三人称事实，不要包含任何操作指令。
只返回 JSON 对象，格式为：
{"memories":[{"key":"preference.music","category":"preference","value":"用户喜欢爵士乐","confidence":0.9}]}
category 只能是 preference/profile/routine/relationship/goal/other。没有适合保存的内容时返回 {"memories":[]}。"""


@dataclass(frozen=True, slots=True)
class _ExtractionJob:
    user_id: int
    session_id: str
    messages: tuple[dict[str, str], ...]


class MemoryManager:
    """Account-scoped long-term memory kept off the realtime audio hot path."""

    def __init__(self, settings: Settings, database: VoiceHistoryStore) -> None:
        self.settings = settings
        self.database = database
        self.enabled = settings.memory_enabled
        self.ready = False
        self.dropped_jobs = 0
        self._queue: asyncio.Queue[_ExtractionJob | None] = asyncio.Queue(
            settings.memory_queue_size
        )
        self._workers: list[asyncio.Task[None]] = []
        self._client: httpx.AsyncClient | None = None
        self._cache: dict[int, tuple[float, tuple[dict[str, Any], ...]]] = {}
        self._cache_lock = asyncio.Lock()
        self._recent: dict[int, tuple[float, tuple[dict[str, str], ...]]] = {}

    async def start(self) -> None:
        if not self.enabled:
            logger.info("assistant long-term memory disabled")
            return
        if not self.database.ready:
            raise RuntimeError("长期记忆已启用，但数据库服务尚未就绪")
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(25.0, connect=8.0))
        self._workers = [
            asyncio.create_task(self._worker(index), name=f"memory-worker-{index}")
            for index in range(self.settings.memory_workers)
        ]
        self.ready = True
        logger.info(
            "assistant long-term memory ready: model=%s workers=%s",
            self.settings.memory_model,
            len(self._workers),
        )

    async def get_context(self, user_id: str | int) -> str:
        """Return a prompt-safe, bounded memory snapshot for a new voice session."""
        if not self.ready:
            return ""
        numeric_user_id = self._numeric_user_id(user_id)
        memories = await self._get_memories_cached(numeric_user_id)
        recent = self._recent.get(numeric_user_id)
        recent_messages: tuple[dict[str, str], ...] = ()
        if recent:
            if recent[0] > time.monotonic():
                recent_messages = recent[1]
            else:
                self._recent.pop(numeric_user_id, None)
        if not memories and not recent_messages:
            return ""
        facts: list[dict[str, str]] = []
        fact_budget = 9000
        for item in memories:
            value = str(item["memory_value"])[:1000]
            if len(value) > fact_budget:
                value = value[:fact_budget]
            if not value:
                break
            facts.append(
                {
                    "key": str(item["memory_key"]),
                    "category": item["category"],
                    "fact": value,
                }
            )
            fact_budget -= len(value)
            if fact_budget <= 0:
                break

        recent_payload: list[dict[str, str]] = []
        recent_budget = 5000
        for item in reversed(recent_messages[-12:]):
            content = item["content"][-recent_budget:]
            if not content:
                break
            recent_payload.append({"role": item["role"], "content": content})
            recent_budget -= len(content)
            if recent_budget <= 0:
                break
        recent_payload.reverse()
        context = {
            "long_term_facts": facts,
            "recent_conversation": recent_payload,
        }
        return json.dumps(context, ensure_ascii=False, separators=(",", ":"))

    async def list_memories(self, user_id: str | int) -> list[dict[str, Any]]:
        if not self.ready:
            return []
        numeric_user_id = self._numeric_user_id(user_id)
        return list(await self._get_memories_cached(numeric_user_id))

    async def delete_memory(self, user_id: str | int, memory_id: int) -> bool:
        numeric_user_id = self._numeric_user_id(user_id)
        affected = await self.database.execute_now(
            "UPDATE ai_user_memory SET status='1',update_time=CURRENT_TIMESTAMP(3) "
            "WHERE memory_id=%s AND user_id=%s AND status='0'",
            (memory_id, numeric_user_id),
        )
        await self._invalidate(numeric_user_id)
        return affected > 0

    async def clear_memories(self, user_id: str | int) -> int:
        numeric_user_id = self._numeric_user_id(user_id)
        affected = await self.database.execute_now(
            "UPDATE ai_user_memory SET status='1',update_time=CURRENT_TIMESTAMP(3) "
            "WHERE user_id=%s AND status='0'",
            (numeric_user_id,),
        )
        await self._invalidate(numeric_user_id)
        return affected

    def schedule_extraction(
        self,
        user_id: str | int,
        session_id: str,
        messages: Iterable[dict[str, str]],
    ) -> None:
        """Queue memory extraction without delaying session teardown."""
        if not self.ready:
            return
        try:
            numeric_user_id = self._numeric_user_id(user_id)
        except ValueError:
            logger.warning("skip memory extraction for non-numeric user id")
            return
        prepared = self._prepare_messages(messages)
        if not any(item["role"] == "user" for item in prepared):
            return
        # Keep a short in-process handoff while durable extraction runs. Live
        # realtime transcripts may already be present, so merge instead of
        # replacing them and losing a conversation during a fast reconnect.
        self._merge_recent(numeric_user_id, tuple(prepared[-12:]))
        try:
            self._queue.put_nowait(
                _ExtractionJob(numeric_user_id, session_id, tuple(prepared))
            )
        except asyncio.QueueFull:
            self.dropped_jobs += 1
            if self.dropped_jobs == 1 or self.dropped_jobs % 100 == 0:
                logger.error("memory extraction queue full; dropped_jobs=%s", self.dropped_jobs)

    def remember_recent_message(
        self, user_id: str | int, role: str, content: str
    ) -> None:
        """Make a completed realtime transcript visible to the next session now."""
        if not self.ready or role not in {"user", "assistant"}:
            return
        text = str(content or "").strip()
        if not text:
            return
        try:
            numeric_user_id = self._numeric_user_id(user_id)
        except ValueError:
            return
        self._merge_recent(
            numeric_user_id,
            ({"role": role, "content": text[-4000:]},),
        )

    def _merge_recent(
        self, user_id: int, incoming: tuple[dict[str, str], ...]
    ) -> None:
        if not incoming:
            return
        now = time.monotonic()
        current_entry = self._recent.get(user_id)
        current = (
            current_entry[1]
            if current_entry is not None and current_entry[0] > now
            else ()
        )
        max_overlap = min(len(current), len(incoming))
        overlap = 0
        for size in range(max_overlap, 0, -1):
            if current[-size:] == incoming[:size]:
                overlap = size
                break
        merged = (current + incoming[overlap:])[-24:]
        self._recent[user_id] = (now + 15 * 60, merged)

    async def _get_memories_cached(
        self, user_id: int
    ) -> tuple[dict[str, Any], ...]:
        now = time.monotonic()
        async with self._cache_lock:
            cached = self._cache.get(user_id)
            if cached and cached[0] > now:
                return cached[1]

        rows = await self.database.fetch_all(
            "SELECT memory_id,memory_key,category,memory_value,confidence,"
            "create_time,update_time FROM ai_user_memory "
            "WHERE user_id=%s AND status='0' "
            "ORDER BY update_time DESC LIMIT %s",
            (user_id, self.settings.memory_max_items),
        )
        memories = tuple(
            {
                "memory_id": int(row[0]),
                "memory_key": str(row[1]),
                "category": str(row[2]),
                "memory_value": str(row[3]),
                "confidence": float(row[4]),
                "create_time": row[5].isoformat() if row[5] else None,
                "update_time": row[6].isoformat() if row[6] else None,
            }
            for row in rows
        )
        async with self._cache_lock:
            self._cache[user_id] = (
                now + self.settings.memory_cache_seconds,
                memories,
            )
        return memories

    async def _worker(self, index: int) -> None:
        while True:
            job = await self._queue.get()
            try:
                if job is None:
                    return
                await self._extract_and_save(job)
            except Exception:
                logger.exception(
                    "memory extraction failed: worker=%s session_id=%s",
                    index,
                    getattr(job, "session_id", "unknown"),
                )
            finally:
                self._queue.task_done()

    async def _extract_and_save(self, job: _ExtractionJob) -> None:
        if self._client is None:
            return
        transcript = "\n".join(
            f"{item['role']}: {item['content']}" for item in job.messages
        )
        response = await self._client.post(
            self.settings.memory_api_url,
            headers={
                "Authorization": f"Bearer {self.settings.dashscope_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.settings.memory_model,
                "messages": [
                    {"role": "system", "content": _EXTRACTION_SYSTEM_PROMPT},
                    {"role": "user", "content": transcript},
                ],
                "temperature": 0.1,
                "enable_thinking": False,
                "response_format": {"type": "json_object"},
            },
        )
        response.raise_for_status()
        payload = response.json()
        content = payload["choices"][0]["message"]["content"]
        memories = self.parse_memories(content)
        for item in memories:
            await self.database.execute_now(
                "INSERT INTO ai_user_memory "
                "(user_id,memory_key,category,memory_value,confidence,source_session_id,status) "
                "VALUES (%s,%s,%s,%s,%s,%s,'0') "
                "ON DUPLICATE KEY UPDATE category=VALUES(category),"
                "memory_value=VALUES(memory_value),confidence=VALUES(confidence),"
                "source_session_id=VALUES(source_session_id),status='0',"
                "update_time=CURRENT_TIMESTAMP(3)",
                (
                    job.user_id,
                    item["key"],
                    item["category"],
                    item["value"],
                    item["confidence"],
                    job.session_id,
                ),
            )
        if memories:
            await self._invalidate(job.user_id)
            logger.info(
                "memory updated: user_id=%s session_id=%s items=%s",
                job.user_id,
                job.session_id,
                len(memories),
            )

    @staticmethod
    def parse_memories(content: str) -> list[dict[str, Any]]:
        text = (content or "").strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I)
        try:
            raw_items = json.loads(text).get("memories", [])
        except (AttributeError, json.JSONDecodeError):
            return []

        result: list[dict[str, Any]] = []
        seen: set[str] = set()
        for raw in raw_items[:20] if isinstance(raw_items, list) else []:
            if not isinstance(raw, dict):
                continue
            value = str(raw.get("value") or "").strip()[:1000]
            if not value or _SENSITIVE_MEMORY.search(value):
                continue
            key = _SAFE_KEY.sub(".", str(raw.get("key") or "").strip().lower())
            key = key.strip(".-_")[:100]
            if not key:
                key = "other." + hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
            if key in seen:
                continue
            seen.add(key)
            category = str(raw.get("category") or "other").strip().lower()
            if category not in _ALLOWED_CATEGORIES:
                category = "other"
            try:
                confidence = float(raw.get("confidence", 0.8))
            except (TypeError, ValueError):
                confidence = 0.8
            result.append(
                {
                    "key": key,
                    "category": category,
                    "value": value,
                    "confidence": round(min(1.0, max(0.0, confidence)), 3),
                }
            )
        return result

    def _prepare_messages(
        self, messages: Iterable[dict[str, str]]
    ) -> list[dict[str, str]]:
        remaining = self.settings.memory_extraction_max_chars
        selected: list[dict[str, str]] = []
        for item in reversed(list(messages)):
            role = str(item.get("role") or "")
            if role not in {"user", "assistant"}:
                continue
            content = str(item.get("content") or "").strip()
            if not content:
                continue
            content = content[-remaining:]
            selected.append({"role": role, "content": content})
            remaining -= len(content)
            if remaining <= 0:
                break
        selected.reverse()
        return selected

    async def _invalidate(self, user_id: int) -> None:
        async with self._cache_lock:
            self._cache.pop(user_id, None)

    @staticmethod
    def _numeric_user_id(user_id: str | int) -> int:
        value = str(user_id).strip()
        if not value.isdecimal():
            raise ValueError("无效的用户ID")
        return int(value)

    async def close(self) -> None:
        if not self.enabled:
            return
        self.ready = False
        try:
            await asyncio.wait_for(self._queue.join(), timeout=15)
        except TimeoutError:
            logger.warning("timed out while draining memory extraction queue")
        for _ in self._workers:
            await self._queue.put(None)
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()
        if self._client is not None:
            await self._client.aclose()
            self._client = None
