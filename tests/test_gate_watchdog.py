import pytest
import time
from unittest.mock import MagicMock
from commands.gate_operation_coordinator import GateOperationCoordinator
from commands.gate_state_monitor import GateStateMonitor, GATE_OPEN, GATE_CLOSED, GATE_MOVING, GATE_STUCK
import config

@pytest.fixture
def fake_controller():
    controller = MagicMock()
    return controller

@pytest.fixture
def mock_monitor(monkeypatch):
    monkeypatch.setattr(config, "MOCK_HARDWARE", True)
    monitor = GateStateMonitor()
    # Start thread not strictly needed for tests if we manipulate mock state 
    # but we will just manually set state. 
    return monitor

def test_watchdog_reaches_target_state(fake_controller, mock_monitor, monkeypatch):
    monkeypatch.setattr(config, "GATE_PULSE_RESPONSE_SECONDS", 0.05)
    monkeypatch.setattr(config, "GATE_RETRY_COOLDOWN_SECONDS", 0.05)
    
    coordinator = GateOperationCoordinator(fake_controller, mock_monitor)
    mock_monitor.set_mock_state(GATE_OPEN)
    
    # We trigger GATE_OPEN. The state is already GATE_OPEN, but it will send one pulse.
    coordinator.trigger_gate(GATE_OPEN)
    time.sleep(0.15)
    
    fake_controller.open.assert_called_once()
    assert coordinator.comando_ativo_pelo_sistema is False

def test_watchdog_retries_and_stuck(fake_controller, mock_monitor, monkeypatch):
    monkeypatch.setattr(config, "GATE_PULSE_RESPONSE_SECONDS", 0.05)
    monkeypatch.setattr(config, "GATE_RETRY_COOLDOWN_SECONDS", 0.05)
    monkeypatch.setattr(config, "GATE_MAX_RETRY_ATTEMPTS", 2)
    
    coordinator = GateOperationCoordinator(fake_controller, mock_monitor)
    
    updates = []
    coordinator.on_state_update = lambda s: updates.append(s)
    
    # Keep it moving so it never reaches GATE_OPEN
    mock_monitor.set_mock_state(GATE_MOVING)
    
    coordinator.trigger_gate(GATE_OPEN)
    
    # Pulses = 1 (initial) + 2 (retries) = 3
    # Wait enough for all retries + cooldowns
    time.sleep(0.5)
    
    assert fake_controller.open.call_count == 3
    assert GATE_STUCK in updates

def test_watchdog_external_movement(fake_controller, mock_monitor, monkeypatch):
    coordinator = GateOperationCoordinator(fake_controller, mock_monitor)
    
    # Trigger a callback without the system commanding it
    assert coordinator.comando_ativo_pelo_sistema is False
    
    # Simulating the monitor changing state (monitor calls _handle_state_change)
    mock_monitor._on_state_change(GATE_OPEN)
    
    # External movement shouldn't trigger any pulses
    fake_controller.open.assert_not_called()
