import asyncio

from assistant_server.config import Settings
from assistant_server.history import VoiceHistoryStore


def test_disabled_history_is_a_noop(monkeypatch):
    monkeypatch.setenv("DATABASE_ENABLED", "false")

    async def run():
        store = VoiceHistoryStore(Settings.from_env())
        await store.start()
        store.start_session(
            session_id="session",
            user_key="1",
            ruoyi_user_id=1,
            client_id="client",
            client_ip="127.0.0.1",
            user_agent="test",
            model_name="model",
            voice_name="voice",
        )
        store.finish_session(
            session_id="session",
            status="closed",
            duration_ms=1,
            message_count=0,
            input_text_chars=0,
            output_text_chars=0,
            close_reason="test",
        )
        await store.close()
        assert not store.ready
        assert store.dropped_events == 0

    asyncio.run(run())

