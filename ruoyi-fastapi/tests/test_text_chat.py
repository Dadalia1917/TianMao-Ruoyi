import pytest

from assistant_server.config import Settings
from assistant_server.text_chat import TextChatError, TextChatService


def test_text_model_catalog_uses_stable_ui_names(monkeypatch):
    monkeypatch.setenv("TEXT_MODEL_QWEN38", "qwen3.8-max-custom")
    service = TextChatService(Settings.from_env())
    catalog = service.model_catalog()

    assert [item["key"] for item in catalog] == [
        "qwen3.8-max",
        "qwen3.7-plus",
        "qwen3.7-flash",
        "deepseek-v4-pro",
        "deepseek-v4-flash",
        "deepseek-r1",
    ]
    assert service._models["qwen3.8-max"].model_id == "qwen3.8-max-custom"
    assert service._models["deepseek-r1"].model_id == "deepseek-r1-0528"
    assert service._models["deepseek-r1"].enable_thinking_parameter is False


def test_model_identity_matches_the_selected_provider():
    service = TextChatService(Settings.from_env())

    qwen_prompt = service._models["qwen3.7-plus"].identity_name
    deepseek_prompt = service._models["deepseek-v4-flash"].identity_name

    assert qwen_prompt == "通义千问（Qwen）"
    assert deepseek_prompt == "DeepSeek"
    assert "天猫" not in qwen_prompt
    assert "天猫" not in deepseek_prompt


def test_smart_panel_text_chat_rejects_image_attachments():
    service = TextChatService(Settings.from_env())
    messages = [
        {
            "role": "user",
            "content": "这是什么？",
            "image": "data:image/png;base64,aGVsbG8=",
        }
    ]

    with pytest.raises(TextChatError) as error:
        service._sanitize_messages(messages)
    assert error.value.code == "unsupported_attachment"
