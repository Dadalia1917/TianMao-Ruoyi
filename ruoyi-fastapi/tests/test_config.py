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


def test_local_mysql_credentials_have_team_defaults(monkeypatch):
    monkeypatch.delenv("MYSQL_USER", raising=False)
    monkeypatch.delenv("MYSQL_PASSWORD", raising=False)

    settings = Settings.from_env()

    assert settings.mysql_user == "root"
    assert settings.mysql_password == "123456"


def test_empty_mysql_password_uses_team_default(monkeypatch):
    monkeypatch.setenv("MYSQL_PASSWORD", "")

    assert Settings.from_env().mysql_password == "123456"
