# Dual Reader (IN/OUT) Implementation Plan

> **For Antigravity:** REQUIRED WORKFLOW: Use `.agent/workflows/execute-plan.md` to execute this plan in single-flow mode.

**Goal:** Enable dual RFID readers (IN and OUT) to log direction accurately, and utilize the active-close ultrasonic sensor logic for both.

**Architecture:** We will uncomment the OUT reader in `main.py`. We will also upgrade `GateController.open()` to trigger the new `_pulse_active_close` logic in a thread, eliminating the need for the external 90-second timer in `main.py`. 

**Tech Stack:** Python, RPi.GPIO (mocked), Threading.

---

### Task 1: Add state protection to GateController

**Files:**
- Modify: `commands/gate_controller.py`
- Modify: `tests/test_gate_controller.py`

**Step 1: Write the failing test**

```python
from unittest.mock import patch
import config

def test_gate_controller_prevents_concurrent_opens():
    from commands.gate_controller import GateController
    from unittest.mock import MagicMock
    import threading
    
    controller = GateController()
    controller.is_active = False # New state flag
    
    # Simulate first call setting the flag
    def mock_pulse():
        controller.is_active = True
        
    with patch.object(controller, '_pulse_active_close', side_effect=mock_pulse):
        controller.open()
        # Immediately try again
        controller.open()
        
    # Should only call the underlying pulse once if it was active
    # We will test this by checking the flag mechanism
```
*(Note: A better test checks if `open()` returns early when `self._is_active` is True. We will write that).*

```python
def test_gate_controller_ignores_open_if_active():
    from commands.gate_controller import GateController
    from unittest.mock import MagicMock
    controller = GateController()
    controller._is_active = True # Mocking that it's already running a cycle
    
    with patch("threading.Thread") as mock_thread:
        controller.open()
        mock_thread.assert_not_called() # Should not spawn a new thread
```

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_gate_controller.py::test_gate_controller_ignores_open_if_active -v`
Expected: FAIL (mock_thread is called)

**Step 3: Write minimal implementation**

Modify `GateController.__init__`:
```python
    def __init__(self, sensor=None):
        self._lock = threading.Lock()
        self._gpio_ready = False
        self.sensor = sensor
        self._is_active = False # NEW
```

Modify `GateController.open`:
```python
    def open(self, duration: int = config.GATE_OPEN_DURATION):
        """Aciona o relé por `duration` segundos em thread separada."""
        with self._lock:
            if self._is_active:
                logger.warning("Portão já está em ciclo de abertura/fechamento. Ignorando novo comando.")
                return
            self._is_active = True

        thread = threading.Thread(
            target=self._pulse_active_close, daemon=True
        )
        thread.start()
```

Modify `GateController._pulse_active_close` to reset the flag at the end:
```python
        finally:
            with self._lock:
                self._is_active = False
```

**Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_gate_controller.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add commands/gate_controller.py tests/test_gate_controller.py
git commit -m "feat: add concurrency protection to GateController"
```

---

### Task 2: Refactor main.py for Dual Readers and Active Close

**Files:**
- Modify: `main.py`

**Step 1: Modify `main.py`**
Since `main.py` uses manual testing/visual validation, we directly modify the code.

```python
    def start_readers(port_in: str, port_out: str):
        nonlocal reader_in, reader_out
        if reader_in: reader_in.stop()
        if reader_out: reader_out.stop()
        
        reader_in = RFIDReader("IN", port_in, handle_tag)
        reader_out = RFIDReader("OUT", port_out, handle_tag)
        reader_in.start()
        reader_out.start()
```

Remove `gate_timer` logic entirely from `main.py` (lines 105-117, 136, 162-173).
Replace `handle_tag` authorized block with just `gate.open()`:
```python
    def handle_tag(tag_code: str, direction: str):
        logger.info("Leitura: Tag=%s, Direction=%s", tag_code, direction)
        result = auth.process(tag_code, direction)

        if result.authorized:
            logger.info("🔓 ACESSO AUTORIZADO para a tag %s", tag_code)
            gate.open()
        else:
            logger.warning("🔒 ACESSO NEGADO para a tag %s. Motivo: %s", tag_code, result.reason)

        if app:
            app.after(0, lambda: [
                app.refresh_all_tabs(),
                app.update_gate_status(result.authorized)
            ])
            # We can still reset UI gate status after a while if we want, or leave it.
            if result.authorized:
                app.after(10000, lambda: app.update_gate_status(False))
```

Remove cleanup logic for `gate_timer` (lines 232-236).

**Step 2: Verify `main.py` syntax**
Run: `python3 -m py_compile main.py`
Expected: No output (success).

**Step 3: Commit**

```bash
git add main.py
git commit -m "feat: enable OUT reader and integrate active close logic"
```
