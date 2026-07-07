def test_config_writes_to_env(tmp_path):
    from unittest.mock import patch
    import config

    env_file = tmp_path / ".env"
    with patch("config.ENV_FILE_PATH", str(env_file)):
        config.update_env("TEST_KEY", "123")

    assert "TEST_KEY='123'" in env_file.read_text()


def test_access_path_is_fixed():
    import config
    assert config.ACCESS_PATH == "/api/raspberry/access"


def test_get_server_base_url_falls_back_to_module_constants(monkeypatch):
    import config
    # Isola o teste de um .env local: zera o env E os defaults de módulo
    # (o config.py carrega .env no import, o que congelaria SERVER_HOST).
    monkeypatch.delenv("SERVER_HOST", raising=False)
    monkeypatch.delenv("SERVER_PORT", raising=False)
    monkeypatch.setattr(config, "SERVER_HOST", "localhost")
    monkeypatch.setattr(config, "SERVER_PORT", "8001")
    assert config.get_server_base_url() == "http://localhost:8001"


def test_get_server_base_url_reads_env_fresh(monkeypatch):
    monkeypatch.setenv("SERVER_HOST", "192.168.0.10")
    monkeypatch.setenv("SERVER_PORT", "9000")
    import config
    assert config.get_server_base_url() == "http://192.168.0.10:9000"


def test_gate_listen_port_default():
    import config
    assert config.GATE_LISTEN_PORT == 8080


def test_gate_open_token_default_empty():
    import config
    assert config.GATE_OPEN_TOKEN == ""
