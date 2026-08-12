from assistant_server.config import Settings


def test_model_query_is_added(monkeypatch):
    monkeypatch.setenv("DASHSCOPE_REALTIME_URL", "wss://example.test/realtime?workspace=a")
    monkeypatch.setenv("DASHSCOPE_MODEL", "demo-model")
    url = Settings.from_env().dashscope_ws_url
    assert "workspace=a" in url
    assert "model=demo-model" in url


def test_ruoyi_auth_is_required_by_configuration(monkeypatch):
    monkeypatch.setenv("RUOYI_AUTH_URL", "not-a-url")
    assert "RUOYI_AUTH_URL 必须是 http:// 或 https:// 地址" in Settings.from_env().validate()
