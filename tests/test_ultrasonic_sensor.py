import pytest
from unittest.mock import MagicMock, patch
from commands.ultrasonic_sensor import UltrasonicSensor

def test_sensor_mock_mode():
    with patch("config.MOCK_HARDWARE", True):
        sensor = UltrasonicSensor()
        assert sensor.is_vehicle_present() is False
