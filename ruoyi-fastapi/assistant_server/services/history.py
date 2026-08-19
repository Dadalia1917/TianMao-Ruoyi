from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

from ..core.config import Settings

logger = logging.getLogger(__name__)

_MEMORY_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS ai_user_memory (
  memory_id bigint NOT NULL AUTO_INCREMENT COMMENT '记忆ID',
  user_id bigint NOT NULL COMMENT '若依用户ID，作为账号隔离边界',
  memory_key varchar(100) CHARACTER SET ascii COLLATE ascii_general_ci NOT NULL COMMENT '稳定记忆键',
  category varchar(32) CHARACTER SET ascii COLLATE ascii_general_ci NOT NULL DEFAULT 'other' COMMENT '记忆分类',
  memory_value varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '长期记忆',
  confidence decimal(4,3) NOT NULL DEFAULT 0.800 COMMENT '记忆置信度',
  source_session_id varchar(36) CHARACTER SET ascii COLLATE ascii_general_ci NULL DEFAULT NULL COMMENT '来源会话ID',
  status char(1) CHARACTER SET ascii COLLATE ascii_general_ci NOT NULL DEFAULT '0' COMMENT '0有效 1已删除',
  last_used_at datetime(3) NULL DEFAULT NULL COMMENT '最近注入模型时间',
  create_time datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '创建时间',
  update_time datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3) COMMENT '更新时间',
  PRIMARY KEY (memory_id),
  UNIQUE INDEX uk_ai_user_memory_key(user_id, memory_key),
  INDEX idx_ai_user_memory_user_status(user_id, status, update_time DESC)
) ENGINE=InnoDB CHARACTER SET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='天猫智家账号长期记忆表' ROW_FORMAT=DYNAMIC
"""


@dataclass(frozen=True, slots=True)
class _DatabaseEvent:
    kind: str
    session_id: str
    values: tuple[Any, ...]


class VoiceHistoryStore:
    """Non-blocking, sharded persistence for voice metadata and transcripts.

    Every session is consistently assigned to one worker queue, so its start,
    messages and finish operations keep their order while unrelated users can
    still be written concurrently.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.enabled = settings.database_enabled
        self.ready = False
        self.dropped_events = 0
        self._pool: Any = None
        self._queues: list[asyncio.Queue[_DatabaseEvent | None]] = []
        self._workers: list[asyncio.Task[None]] = []

    async def start(self) -> None:
        if not self.enabled:
            logger.info("voice history persistence disabled")
            return
        try:
            import aiomysql
        except ImportError as exc:
            raise RuntimeError(
                "已启用数据库持久化，但缺少 aiomysql；请执行 pip install -r requirements.txt"
            ) from exc

        worker_count = min(self.settings.database_workers, self.settings.mysql_pool_max_size)
        shard_size = max(100, self.settings.database_queue_size // worker_count)
        self._queues = [asyncio.Queue(shard_size) for _ in range(worker_count)]
        self._pool = await aiomysql.create_pool(
            host=self.settings.mysql_host,
            port=self.settings.mysql_port,
            user=self.settings.mysql_user,
            password=self.settings.mysql_password,
            db=self.settings.mysql_database,
            charset="utf8mb4",
            autocommit=True,
            minsize=self.settings.mysql_pool_min_size,
            maxsize=self.settings.mysql_pool_max_size,
            connect_timeout=8,
        )
        await self._ensure_managed_schema()
        await self._verify_schema()
        self._workers = [
            asyncio.create_task(self._worker(index), name=f"voice-db-{index}")
            for index in range(worker_count)
        ]
        self.ready = True
        logger.info(
            "voice history persistence ready: database=%s workers=%s transcripts=%s",
            self.settings.mysql_database,
            worker_count,
            self.settings.voice_store_transcripts,
        )

    async def _ensure_managed_schema(self) -> None:
        """Create only the assistant-owned memory table for one-command startup."""
        if not self.settings.memory_enabled:
            return
        async with self._pool.acquire() as connection:
            async with connection.cursor() as cursor:
                await cursor.execute(_MEMORY_TABLE_DDL)

    async def _verify_schema(self) -> None:
        required_tables = ["ai_voice_session", "ai_voice_message"]
        if self.settings.memory_enabled:
            required_tables.append("ai_user_memory")
        placeholders = ",".join(["%s"] * len(required_tables))
        async with self._pool.acquire() as connection:
            async with connection.cursor() as cursor:
                await cursor.execute(
                    "SELECT COUNT(*) FROM information_schema.tables "
                    f"WHERE table_schema=%s AND table_name IN ({placeholders})",
                    (self.settings.mysql_database, *required_tables),
                )
                row = await cursor.fetchone()
        if not row or int(row[0]) != len(required_tables):
            self._pool.close()
            await self._pool.wait_closed()
            self._pool = None
            raise RuntimeError(
                "数据库缺少智能语音或记忆表，请执行 sql/tmall-smart-home-assistant-upgrade.sql；"
                "新数据库可直接执行 sql/ry-cat.sql"
            )

    async def fetch_all(
        self, statement: str, values: tuple[Any, ...] = ()
    ) -> tuple[tuple[Any, ...], ...]:
        """Run a small account-scoped query through the shared async pool."""
        self._require_ready()
        async with self._pool.acquire() as connection:
            async with connection.cursor() as cursor:
                await cursor.execute(statement, values)
                rows = await cursor.fetchall()
        return tuple(rows)

    async def execute_now(self, statement: str, values: tuple[Any, ...] = ()) -> int:
        """Execute an immediate management write and return affected rows."""
        self._require_ready()
        async with self._pool.acquire() as connection:
            async with connection.cursor() as cursor:
                await cursor.execute(statement, values)
                return int(cursor.rowcount)

    def _require_ready(self) -> None:
        if not self.enabled or not self.ready or self._pool is None:
            raise RuntimeError("数据库服务尚未就绪")

    def start_session(
        self,
        *,
        session_id: str,
        user_key: str,
        ruoyi_user_id: int | None,
        client_id: str,
        client_ip: str,
        user_agent: str,
        model_name: str,
        voice_name: str,
    ) -> None:
        self._enqueue(
            _DatabaseEvent(
                "start",
                session_id,
                (
                    session_id,
                    user_key,
                    ruoyi_user_id,
                    client_id,
                    client_ip,
                    user_agent,
                    model_name,
                    voice_name,
                ),
            )
        )

    def activate_session(self, session_id: str, qwen_session_id: str) -> None:
        self._enqueue(_DatabaseEvent("activate", session_id, (qwen_session_id or None, session_id)))

    def add_message(
        self,
        *,
        session_id: str,
        sequence_no: int,
        role: str,
        content: str,
        qwen_item_id: str,
    ) -> None:
        if not self.settings.voice_store_transcripts:
            return
        self._enqueue(
            _DatabaseEvent(
                "message",
                session_id,
                (session_id, sequence_no, role, content, qwen_item_id or None),
            )
        )

    def finish_session(
        self,
        *,
        session_id: str,
        status: str,
        duration_ms: int,
        message_count: int,
        input_text_chars: int,
        output_text_chars: int,
        close_reason: str,
    ) -> None:
        self._enqueue(
            _DatabaseEvent(
                "finish",
                session_id,
                (
                    status,
                    max(0, duration_ms),
                    max(0, message_count),
                    max(0, input_text_chars),
                    max(0, output_text_chars),
                    close_reason[:255] or None,
                    session_id,
                ),
            )
        )

    def _enqueue(self, event: _DatabaseEvent) -> None:
        if not self.enabled or not self.ready or not self._queues:
            return
        queue = self._queues[hash(event.session_id) % len(self._queues)]
        try:
            queue.put_nowait(event)
        except asyncio.QueueFull:
            self.dropped_events += 1
            if self.dropped_events == 1 or self.dropped_events % 100 == 0:
                logger.error(
                    "voice history queue full; dropped_events=%s",
                    self.dropped_events,
                )

    async def _worker(self, index: int) -> None:
        queue = self._queues[index]
        while True:
            event = await queue.get()
            try:
                if event is None:
                    return
                await self._execute(event)
            except Exception:
                logger.exception(
                    "voice history write failed: kind=%s session_id=%s",
                    getattr(event, "kind", "unknown"),
                    getattr(event, "session_id", "unknown"),
                )
            finally:
                queue.task_done()

    async def _execute(self, event: _DatabaseEvent) -> None:
        statements = {
            "start": (
                "INSERT INTO ai_voice_session "
                "(session_id,user_key,user_id,client_id,client_ip,user_agent,"
                "model_name,voice_name,status) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'connecting')"
            ),
            "activate": (
                "UPDATE ai_voice_session SET qwen_session_id=%s,status='active' WHERE session_id=%s"
            ),
            "message": (
                "INSERT INTO ai_voice_message "
                "(session_id,sequence_no,role,content,qwen_item_id) "
                "VALUES (%s,%s,%s,%s,%s)"
            ),
            "finish": (
                "UPDATE ai_voice_session SET status=%s,ended_at=CURRENT_TIMESTAMP(3),"
                "duration_ms=%s,message_count=%s,input_text_chars=%s,"
                "output_text_chars=%s,close_reason=%s WHERE session_id=%s"
            ),
        }
        statement = statements[event.kind]
        async with self._pool.acquire() as connection:
            async with connection.cursor() as cursor:
                await cursor.execute(statement, event.values)

    async def close(self) -> None:
        if not self.enabled or not self._pool:
            return
        try:
            await asyncio.wait_for(
                asyncio.gather(*(queue.join() for queue in self._queues)),
                timeout=8,
            )
        except TimeoutError:
            logger.warning("timed out while draining voice history queues")
        for queue in self._queues:
            await queue.put(None)
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._pool.close()
        await self._pool.wait_closed()
        self.ready = False
