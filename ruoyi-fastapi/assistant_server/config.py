from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def load_local_env(path: Path) -> None:
    """Load a small .env file without adding another runtime dependency."""
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


def _as_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_int(name: str, default: int, minimum: int = 1) -> int:
    try:
        return max(minimum, int(os.getenv(name, str(default))))
    except ValueError:
        return default


@dataclass(frozen=True, slots=True)
class Settings:
    dashscope_api_key: str
    dashscope_realtime_url: str
    dashscope_model: str
    dashscope_voice: str
    acoustic_relay_enabled: bool
    acoustic_relay_wake_phrase: str
    host: str
    port: int
    log_level: str
    allowed_origins: tuple[str, ...]
    max_connections: int
    max_connections_per_user: int
    upstream_rotate_seconds: int
    client_event_max_bytes: int
    client_queue_size: int
    ruoyi_auth_url: str
    ruoyi_auth_cache_seconds: int
    database_enabled: bool
    mysql_host: str
    mysql_port: int
    mysql_database: str
    mysql_user: str
    mysql_password: str
    mysql_pool_min_size: int
    mysql_pool_max_size: int
    database_queue_size: int
    database_workers: int
    voice_store_transcripts: bool
    memory_enabled: bool
    memory_api_url: str
    memory_model: str
    memory_cache_seconds: int
    memory_max_items: int
    memory_queue_size: int
    memory_workers: int
    memory_extraction_max_chars: int
    text_chat_enabled: bool
    text_chat_api_url: str
    text_model_qwen38: str
    text_model_qwen37: str
    text_model_qwen37_flash: str
    text_model_deepseek: str
    text_model_deepseek_pro: str
    text_model_deepseek_r1: str
    text_max_connections: int
    text_max_connections_per_user: int
    text_request_max_bytes: int
    text_max_messages: int
    text_max_chars: int
    text_timeout_seconds: int

    @classmethod
    def from_env(cls) -> "Settings":
        origins = tuple(
            item.strip()
            for item in os.getenv("ALLOWED_ORIGINS", "*").split(",")
            if item.strip()
        )
        return cls(
            dashscope_api_key=os.getenv("DASHSCOPE_API_KEY", "").strip(),
            dashscope_realtime_url=os.getenv(
                "DASHSCOPE_REALTIME_URL",
                "wss://dashscope.aliyuncs.com/api-ws/v1/realtime",
            ).strip(),
            dashscope_model=os.getenv(
                "DASHSCOPE_MODEL", "qwen3.5-omni-plus-realtime"
            ).strip(),
            dashscope_voice=os.getenv("DASHSCOPE_VOICE", "Ethan").strip(),
            acoustic_relay_enabled=_as_bool("ACOUSTIC_RELAY_ENABLED", True),
            acoustic_relay_wake_phrase=os.getenv(
                "ACOUSTIC_RELAY_WAKE_PHRASE", "天猫精灵"
            ).strip()
            or "天猫精灵",
            host=os.getenv("HOST", "0.0.0.0").strip(),
            port=_as_int("PORT", 8001),
            log_level=os.getenv("LOG_LEVEL", "info").strip().lower(),
            allowed_origins=origins or ("*",),
            max_connections=_as_int("MAX_CONNECTIONS", 300),
            max_connections_per_user=_as_int("MAX_CONNECTIONS_PER_USER", 3),
            upstream_rotate_seconds=_as_int("UPSTREAM_ROTATE_SECONDS", 6900, 300),
            client_event_max_bytes=_as_int("CLIENT_EVENT_MAX_BYTES", 262_144, 4096),
            client_queue_size=_as_int("CLIENT_QUEUE_SIZE", 256, 16),
            ruoyi_auth_url=os.getenv(
                "RUOYI_AUTH_URL", "http://127.0.0.1:8080/getInfo"
            ).strip(),
            ruoyi_auth_cache_seconds=_as_int("RUOYI_AUTH_CACHE_SECONDS", 60),
            database_enabled=_as_bool("DATABASE_ENABLED", True),
            mysql_host=os.getenv("MYSQL_HOST", "127.0.0.1").strip(),
            mysql_port=_as_int("MYSQL_PORT", 3306),
            mysql_database=os.getenv("MYSQL_DATABASE", "ry-cat").strip(),
            mysql_user=os.getenv("MYSQL_USER", "root").strip(),
            mysql_password=os.getenv("MYSQL_PASSWORD", ""),
            mysql_pool_min_size=_as_int("MYSQL_POOL_MIN_SIZE", 2),
            mysql_pool_max_size=_as_int("MYSQL_POOL_MAX_SIZE", 20),
            database_queue_size=_as_int("DATABASE_QUEUE_SIZE", 10_000, 100),
            database_workers=_as_int("DATABASE_WORKERS", 2),
            voice_store_transcripts=_as_bool("VOICE_STORE_TRANSCRIPTS", False),
            memory_enabled=_as_bool("MEMORY_ENABLED", True),
            memory_api_url=os.getenv(
                "MEMORY_API_URL",
                "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
            ).strip(),
            memory_model=os.getenv("MEMORY_MODEL", "qwen-plus").strip(),
            memory_cache_seconds=_as_int("MEMORY_CACHE_SECONDS", 300, 10),
            memory_max_items=_as_int("MEMORY_MAX_ITEMS", 50, 1),
            memory_queue_size=_as_int("MEMORY_QUEUE_SIZE", 2000, 10),
            memory_workers=_as_int("MEMORY_WORKERS", 2, 1),
            memory_extraction_max_chars=_as_int(
                "MEMORY_EXTRACTION_MAX_CHARS", 16000, 1000
            ),
            text_chat_enabled=_as_bool("TEXT_CHAT_ENABLED", True),
            text_chat_api_url=os.getenv(
                "TEXT_CHAT_API_URL",
                "https://dashscope.aliyuncs.com/compatible-mode/v1",
            ).strip(),
            text_model_qwen38=os.getenv(
                "TEXT_MODEL_QWEN38", "qwen3.8-max"
            ).strip(),
            text_model_qwen37=os.getenv(
                "TEXT_MODEL_QWEN37", "qwen3.7-plus-2026-05-26"
            ).strip(),
            text_model_qwen37_flash=os.getenv(
                "TEXT_MODEL_QWEN37_FLASH", "qwen3.7-flash-2026-07-15"
            ).strip(),
            text_model_deepseek=os.getenv(
                "TEXT_MODEL_DEEPSEEK", "deepseek-v4-flash-0731"
            ).strip(),
            text_model_deepseek_pro=os.getenv(
                "TEXT_MODEL_DEEPSEEK_PRO", "deepseek-v4-pro"
            ).strip(),
            text_model_deepseek_r1=os.getenv(
                "TEXT_MODEL_DEEPSEEK_R1", "deepseek-r1-0528"
            ).strip(),
            text_max_connections=_as_int("TEXT_MAX_CONNECTIONS", 100, 1),
            text_max_connections_per_user=_as_int(
                "TEXT_MAX_CONNECTIONS_PER_USER", 3, 1
            ),
            text_request_max_bytes=_as_int(
                "TEXT_REQUEST_MAX_BYTES", 524_288, 65_536
            ),
            text_max_messages=_as_int("TEXT_MAX_MESSAGES", 30, 2),
            text_max_chars=_as_int("TEXT_MAX_CHARS", 60_000, 1000),
            text_timeout_seconds=_as_int("TEXT_TIMEOUT_SECONDS", 240, 30),
        )

    @property
    def dashscope_ws_url(self) -> str:
        """Append the model query once while preserving workspace query params."""
        parts = urlsplit(self.dashscope_realtime_url)
        query = dict(parse_qsl(parts.query, keep_blank_values=True))
        query.setdefault("model", self.dashscope_model)
        return urlunsplit(
            (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
        )

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.ruoyi_auth_url.startswith(("http://", "https://")):
            errors.append("RUOYI_AUTH_URL 必须是 http:// 或 https:// 地址")
        if not self.dashscope_realtime_url.startswith(("ws://", "wss://")):
            errors.append("DASHSCOPE_REALTIME_URL 必须是 ws:// 或 wss:// 地址")
        if self.database_enabled and not self.mysql_database:
            errors.append("DATABASE_ENABLED=true 时必须配置 MYSQL_DATABASE")
        if self.mysql_pool_min_size > self.mysql_pool_max_size:
            errors.append("MYSQL_POOL_MIN_SIZE 不能大于 MYSQL_POOL_MAX_SIZE")
        if self.memory_enabled and not self.database_enabled:
            errors.append("MEMORY_ENABLED=true 时必须同时启用 DATABASE_ENABLED")
        if self.memory_enabled and not self.memory_api_url.startswith(
            ("http://", "https://")
        ):
            errors.append("MEMORY_API_URL 必须是 http:// 或 https:// 地址")
        if self.text_chat_enabled and not self.text_chat_api_url.startswith(
            ("http://", "https://")
        ):
            errors.append("TEXT_CHAT_API_URL 必须是 http:// 或 https:// 地址")
        if self.text_chat_enabled and not all(
            (
                self.text_model_qwen38,
                self.text_model_qwen37,
                self.text_model_qwen37_flash,
                self.text_model_deepseek,
                self.text_model_deepseek_pro,
                self.text_model_deepseek_r1,
            )
        ):
            errors.append("文字对话模型 ID 不能为空")
        return errors
