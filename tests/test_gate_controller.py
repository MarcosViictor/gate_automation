import pytest
from unittest.mock import MagicMock
from commands.gate_controller import GateController

def test_gate_controller_accepts_sensor():
    mock_sensor = MagicMock()
    controller = GateController(sensor=mock_sensor)
    assert controller.sensor == mock_sensor
