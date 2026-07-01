import config

def test_ultrasonic_config_variables_exist():
    assert hasattr(config, "ULTRASONIC_TRIGGER_PIN")
    assert hasattr(config, "ULTRASONIC_ECHO_PIN")
    assert hasattr(config, "ULTRASONIC_PRESENCE_THRESHOLD")
    assert hasattr(config, "GATE_SAFE_CLOSE_DELAY")
    assert hasattr(config, "GATE_FALLBACK_TIMEOUT")
