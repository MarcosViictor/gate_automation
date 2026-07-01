# Ultrasonic Sensor Integration Implementation Plan

> **For Antigravity:** REQUIRED WORKFLOW: Use `.agent/workflows/execute-plan.md` to execute this plan in single-flow mode.

**Goal:** Integrate the JSN-SR04T ultrasonic sensor to actively monitor vehicle presence and close the gate safely, eliminating the 90-second blind timeout.

**Architecture:** We will create a dedicated `UltrasonicSensor` hardware class running on a background thread that calculates a moving average of distances to prevent false positives. The `GateController` will use this sensor to monitor a 3-phase state (Waiting, Passing, Passed) and close the gate immediately after the vehicle clears the area, with a conservative fallback timeout.

**Tech Stack:** Python, threading, RPi.GPIO (mocked in tests).

---

### Task 1: Add Configuration Variables

**Files:**
- Modify: `config.py:48-50`
- Test: `tests/test_ultrasonic_config.py` (New file)

**Step 1: Write the failing test**

```python
import config

def test_ultrasonic_config_variables_exist():
    assert hasattr(config, "ULTRASONIC_TRIGGER_PIN")
    assert hasattr(config, "ULTRASONIC_ECHO_PIN")
    assert hasattr(config, "ULTRASONIC_PRESENCE_THRESHOLD")
    assert hasattr(config, "GATE_SAFE_CLOSE_DELAY")
    assert hasattr(config, "GATE_FALLBACK_TIMEOUT")
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_ultrasonic_config.py -v`
Expected: FAIL with "AttributeError: module 'config' has no attribute 'ULTRASONIC_TRIGGER_PIN'"

**Step 3: Write minimal implementation**

```python
# Em config.py, no final do arquivo adicione:
# ==============================================================================
# Sensor Ultrassônico (JSN-SR04T)
# ==============================================================================
ULTRASONIC_TRIGGER_PIN = int(os.getenv("ULTRASONIC_TRIGGER_PIN", "23"))
ULTRASONIC_ECHO_PIN = int(os.getenv("ULTRASONIC_ECHO_PIN", "24"))
ULTRASONIC_PRESENCE_THRESHOLD = float(os.getenv("ULTRASONIC_PRESENCE_THRESHOLD", "1.5")) # metros
GATE_SAFE_CLOSE_DELAY = int(os.getenv("GATE_SAFE_CLOSE_DELAY", "3")) # segundos
GATE_FALLBACK_TIMEOUT = int(os.getenv("GATE_FALLBACK_TIMEOUT", "120")) # segundos
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_ultrasonic_config.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_ultrasonic_config.py config.py
git commit -m "feat: add ultrasonic sensor config variables"
```

---

### Task 2: Create the UltrasonicSensor Class

**Files:**
- Create: `commands/ultrasonic_sensor.py`
- Create: `tests/test_ultrasonic_sensor.py`

**Step 1: Write the failing test**

```python
import pytest
from unittest.mock import MagicMock, patch
from commands.ultrasonic_sensor import UltrasonicSensor

def test_sensor_mock_mode():
    with patch("config.MOCK_HARDWARE", True):
        sensor = UltrasonicSensor()
        assert sensor.is_vehicle_present() is False
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_ultrasonic_sensor.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'commands.ultrasonic_sensor'"

**Step 3: Write minimal implementation**

```python
import config
import logging
import threading
import time

logger = logging.getLogger(__name__)

class UltrasonicSensor:
    def __init__(self):
        self._distance = 9.9
        self._ready = False
        if not config.MOCK_HARDWARE:
            self._setup_gpio()
            
    def _setup_gpio(self):
        pass # Will implement in next tasks for real hardware

    def is_vehicle_present(self) -> bool:
        if config.MOCK_HARDWARE:
            return False # For now, mock always says no vehicle
        return self._distance < config.ULTRASONIC_PRESENCE_THRESHOLD
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_ultrasonic_sensor.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_ultrasonic_sensor.py commands/ultrasonic_sensor.py
git commit -m "feat: create base UltrasonicSensor class"
```

---

### Task 3: Refactor GateController to accept a Sensor Mock

**Files:**
- Modify: `commands/gate_controller.py`
- Create: `tests/test_gate_controller.py`

**Step 1: Write the failing test**

```python
import pytest
from unittest.mock import MagicMock
from commands.gate_controller import GateController

def test_gate_controller_accepts_sensor():
    mock_sensor = MagicMock()
    controller = GateController(sensor=mock_sensor)
    assert controller.sensor == mock_sensor
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_gate_controller.py -v`
Expected: FAIL with "TypeError: GateController.__init__() got an unexpected keyword argument 'sensor'"

**Step 3: Write minimal implementation**

```python
# In commands/gate_controller.py:
# Modify __init__ to accept sensor
    def __init__(self, sensor=None):
        self._lock = threading.Lock()
        self._gpio_ready = False
        self.sensor = sensor
# ... rest remains
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_gate_controller.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_gate_controller.py commands/gate_controller.py
git commit -m "refactor: allow dependency injection of sensor into GateController"
```

---

### Task 4: Implement Active Closing Logic in GateController

**Files:**
- Modify: `commands/gate_controller.py`
- Modify: `tests/test_gate_controller.py`

**Step 1: Write the failing test**

```python
# append to test_gate_controller.py
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_gate_controller.py::test_gate_active_close_logic -v`
Expected: FAIL with "AttributeError: 'GateController' object has no attribute '_pulse_active_close'"

**Step 3: Write minimal implementation**

```python
# In GateController (commands/gate_controller.py):
    def _pulse_active_close(self):
        if config.MOCK_HARDWARE:
            logger.info("[MOCK] Portão ABERTO (Fechamento Ativo)")
        else:
            self._gpio_open_cmd() # Needs split of _gpio_open

        # Phase 1: Wait for vehicle to arrive
        timeout = time.time() + config.GATE_FALLBACK_TIMEOUT
        vehicle_arrived = False
        while time.time() < timeout:
            if self.sensor and self.sensor.is_vehicle_present():
                vehicle_arrived = True
                break
            time.sleep(0.5)

        # Phase 2: Wait for vehicle to pass completely
        if vehicle_arrived:
            logger.info("Veículo detectado. Aguardando passagem...")
            while self.sensor and self.sensor.is_vehicle_present():
                time.sleep(0.5)
            logger.info("Passagem concluída. Aguardando safe delay...")
            time.sleep(config.GATE_SAFE_CLOSE_DELAY)
        else:
            logger.info("Timeout de fallback atingido. Nenhum veículo passou.")

        if config.MOCK_HARDWARE:
            logger.info("[MOCK] Portão FECHADO (Fechamento Ativo)")
        else:
            self._gpio_close_cmd()

    def _gpio_open_cmd(self):
        if not self._gpio_ready: return
        import RPi.GPIO as GPIO  # type: ignore
        GPIO.setup(config.GATE_RELAY_PIN, GPIO.OUT, initial=GPIO.LOW)

    def _gpio_close_cmd(self):
        if not self._gpio_ready: return
        import RPi.GPIO as GPIO  # type: ignore
        GPIO.setup(config.GATE_RELAY_PIN, GPIO.IN)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_gate_controller.py::test_gate_active_close_logic -v`
Expected: PASS

**Step 5: Commit**

```bash
git add commands/gate_controller.py tests/test_gate_controller.py
git commit -m "feat: implement active closing 3-phase logic"
```
