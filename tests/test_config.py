def test_config_writes_to_env(tmp_path):
    from unittest.mock import patch
    import config
    
    env_file = tmp_path / ".env"
    with patch("config.ENV_FILE_PATH", str(env_file)):
        config.update_env("TEST_KEY", "123")
        
    assert "TEST_KEY='123'" in env_file.read_text()
