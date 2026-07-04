import pytest
import time
from commands.gate_state_monitor import GateStateMonitor, GATE_OPEN, GATE_CLOSED, GATE_MOVING

def test_gate_state_monitor_map_state():
    monitor = GateStateMonitor()
    
    # Truth table
    assert monitor._map_state(0, 1) == GATE_OPEN
    assert monitor._map_state(1, 0) == GATE_OPEN
    assert monitor._map_state(0, 0) == GATE_CLOSED
    assert monitor._map_state(1, 1) == GATE_MOVING

def test_gate_state_monitor_mock_state(monkeypatch):
    import config
    monkeypatch.setattr(config, "MOCK_HARDWARE", True)
    
    monitor = GateStateMonitor()
    assert monitor.get_state() == GATE_MOVING
    
    monitor.set_mock_state(GATE_OPEN)
    assert monitor.get_state() == GATE_OPEN
    
    monitor.set_mock_state(GATE_CLOSED)
    assert monitor.get_state() == GATE_CLOSED

def test_gate_state_monitor_callback(monkeypatch):
    # Need to reduce debounce time for testing quickly
    import config
    monkeypatch.setattr(config, "GATE_STATE_DEBOUNCE_SECONDS", 0.01)
    monkeypatch.setattr(config, "GATE_STATE_POLL_INTERVAL", 0.01)
    monkeypatch.setattr(config, "MOCK_HARDWARE", True)
    
    callbacks = []
    
    def on_change(state):
        callbacks.append(state)
        
    monitor = GateStateMonitor(on_state_change=on_change)
    monitor.start()
    
    # State is initially GATE_MOVING because mock state is initialized as GATE_MOVING
    # Wait for the thread to run a bit
    time.sleep(0.05)
    
    monitor.set_mock_state(GATE_OPEN)
    time.sleep(0.05)
    
    monitor.set_mock_state(GATE_CLOSED)
    time.sleep(0.05)
    
    monitor.stop()
    
    # Callbacks should not contain duplicate initial state if it started moving
    # It should contain exactly the state changes
    assert GATE_OPEN in callbacks
    assert GATE_CLOSED in callbacks
    # Only transitions are logged. Since we started moving, first transition is ABERTO, then FECHADO.
    assert callbacks == [GATE_OPEN, GATE_CLOSED]
