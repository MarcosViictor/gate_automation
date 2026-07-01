import pytest
from unittest.mock import MagicMock
from commands.gate_controller import GateController

def test_gate_controller_accepts_sensor():
    mock_sensor = MagicMock()
    controller = GateController(sensor=mock_sensor)
    assert controller.sensor == mock_sensor

from unittest.mock import patch
import config

@patch("time.sleep")
def test_gate_active_close_logic(mock_sleep):
    mock_sensor = MagicMock()
    # Simulate: Waiting -> Passing -> Passed
    mock_sensor.is_vehicle_present.side_effect = [False, True, False]
    
    with patch("config.MOCK_HARDWARE", True):
        controller = GateController(sensor=mock_sensor)
        controller._pulse_active_close()
    
    # Should check sensor multiple times
    assert mock_sensor.is_vehicle_present.call_count == 3

def test_gate_controller_ignores_open_if_active():
    from commands.gate_controller import GateController
    from unittest.mock import patch
    
    controller = GateController()
    controller._is_active = True
    
    with patch("threading.Thread") as mock_thread:
        controller.open()
        mock_thread.assert_not_called()
