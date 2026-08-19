import asyncio
import json

from assistant_server.core.config import Settings
from assistant_server.services.memory import MemoryManager


def test_parse_memories_sanitizes_model_output():
    result = MemoryManager.parse_memories(
        """```json
        {"memories":[
          {"key":"Preference / Music","category":"preference","value":"用户喜欢爵士乐","confidence":1.4},
          {"key":"Preference / Music","category":"invalid","value":"重复内容","confidence":0.2},
          {"key":"","category":"goal","value":"用户希望坚持晨跑","confidence":"0.85"},
          {"key":"secret","category":"profile","value":"用户的银行卡是 1234","confidence":0.99}
        ]}
        ```"""
    )

    assert len(result) == 2
    assert result[0] == {
        "key": "preference.music",
        "category": "preference",
        "value": "用户喜欢爵士乐",
        "confidence": 1.0,
    }
    assert result[1]["key"].startswith("other.")
    assert result[1]["category"] == "goal"
    assert result[1]["confidence"] == 0.85


def test_live_transcripts_are_available_to_the_next_session_immediately():
    class EmptyDatabase:
        async def fetch_all(self, statement, values):
            return []

    manager = MemoryManager(Settings.from_env(), EmptyDatabase())
    manager.ready = True
    manager.remember_recent_message("1", "user", "我叫科比")
    manager.remember_recent_message("1", "assistant", "很高兴认识你，科比")

    context = json.loads(asyncio.run(manager.get_context("1")))

    assert context["recent_conversation"] == [
        {"role": "user", "content": "我叫科比"},
        {"role": "assistant", "content": "很高兴认识你，科比"},
    ]
