# Gate State Detection with Hall Sensors Implementation Plan

**Goal:** Implement physical gate state detection using two NJK-5002C Hall sensors, integrate it with the existing relay pulse controller, and support the single-pulse/toggle watchdog behavior described in `docs/specs/gate-state-detection-hall-sensors.md`.

**Architecture:** Add a dedicated gate state monitor module for sensor reading and state transitions, then add an orchestration layer in `main.py` that coordinates authorized RFID reads, relay pulses, post-pulse sensor checks, retry limits, external movement detection, UI updates, and clean shutdown.

**Tech Stack:** Python 3, `RPi.GPIO`, threading, Tkinter/ttk, pytest.

---

## Task 1: Add Configuration Constants

**Files:**
* Modify: `config.py`

**Implementation:**
Add the sensor and watchdog configuration values:

```python
GATE_SENSOR_A_PIN = 17
GATE_SENSOR_B_PIN = 27
GATE_STATE_POLL_INTERVAL = 0.05
GATE_STATE_DEBOUNCE_SECONDS = 0.02
GATE_MOVING_TIMEOUT_SECONDS = 30.0
GATE_PULSE_RESPONSE_SECONDS = 10.0
GATE_RETRY_COOLDOWN_SECONDS = 2.0
GATE_MAX_RETRY_ATTEMPTS = 3
GATE_PASSAGE_CONFIRMATION_SECONDS = 30.0
```

Prefer environment-variable overrides for timing values where useful in testing.

**Verification:**
Run:

```bash
python3 -m py_compile config.py
```

---

## Task 2: Create Gate State Monitor

**Files:**
* Create: `commands/gate_state_monitor.py`

**Implementation:**
Create a `GateStateMonitor` responsible for:

* GPIO setup for sensor A and B with `GPIO.PUD_UP`.
* Mock mode support without importing `RPi.GPIO`.
* Debounced sensor reading.
* Truth-table mapping:
  * `LOW, HIGH` -> `ABERTO`
  * `HIGH, LOW` -> `ABERTO`
  * `LOW, LOW` -> `FECHADO`
  * `HIGH, HIGH` -> `EM_ANDAMENTO`
* Threaded polling with `start()` and `stop()`.
* `get_state()` for point-in-time reads.
* Change callback invoked only when state changes.
* Constants:
  * `GATE_OPEN = "ABERTO"`
  * `GATE_CLOSED = "FECHADO"`
  * `GATE_MOVING = "EM_ANDAMENTO"`
  * `GATE_STUCK = "TRAVADO"`

**Design Notes:**
Do not call broad `GPIO.cleanup()` from this class while other GPIO users are active. Prefer cleaning up only owned pins, or coordinate cleanup from application shutdown.

**Verification:**
Run:

```bash
python3 -m py_compile commands/gate_state_monitor.py
```

---

## Task 3: Add Unit Tests for State Mapping and Monitor Behavior

**Files:**
* Create: `tests/test_gate_state_monitor.py`

**Implementation:**
Cover:

* Each truth-table combination.
* Debounce accepting stable readings.
* Repeated state does not emit duplicate callback.
* State change emits callback once.
* Mock mode does not require `RPi.GPIO`.

**Verification:**
Run:

```bash
pytest tests/test_gate_state_monitor.py
```

---

## Task 4: Add Gate Pulse Orchestration Logic

**Files:**
* Modify: `main.py`
* Possibly modify: `commands/gate_controller.py`

**Implementation:**
Introduce an orchestration flow around the existing `GateController.open()` pulse method:

* Track `comando_ativo_pelo_sistema`.
* Track retry count for the active command.
* After each pulse, wait `GATE_PULSE_RESPONSE_SECONDS`.
* Read the current gate state from `GateStateMonitor`.
* Apply post-pulse decision:
  * If result is `ABERTO`, keep open and wait for close timer/passagem flow.
  * If result is `FECHADO` while the original intent was access release, send another pulse to re-open, within retry rules.
  * If result is `EM_ANDAMENTO`, apply cooldown and retry until `GATE_MAX_RETRY_ATTEMPTS`.
  * If retry limit is reached, mark `TRAVADO`.

**Important Constraint:**
The Raspberry Pi sends only a generic pulse. The code must not assume direct control over direction. Naming should avoid implying physical certainty, for example prefer `send_gate_pulse()` or `trigger_gate()` over `open()` in new orchestration code. If `GateController.open()` is kept for compatibility, wrap it with clearer local naming.

**Verification:**
Run:

```bash
python3 -m py_compile main.py commands/gate_controller.py
```

---

## Task 5: Detect External Movement

**Files:**
* Modify: `main.py`

**Implementation:**
When `GateStateMonitor` reports a state change:

* If `comando_ativo_pelo_sistema` is `True`, treat it as part of the active command.
* If `comando_ativo_pelo_sistema` is `False`, log `movimento externo detectado`.
* Do not start watchdog or retry logic for external movement.
* Always update UI state from the physical state.

**Verification:**
Use mock monitor state changes and confirm logs/UI updates occur without relay pulses.

---

## Task 6: Update UI for Four Gate States

**Files:**
* Modify: `views/main_window.py`
* Modify call sites in `main.py`

**Implementation:**
Change:

```python
update_gate_status(is_open: bool)
```

to:

```python
update_gate_status(state: str)
```

Support:

* `ABERTO` -> `PORTAO ABERTO`
* `FECHADO` -> `PORTAO FECHADO`
* `EM_ANDAMENTO` -> `PORTAO EM ANDAMENTO`
* `TRAVADO` -> `PORTAO TRAVADO`

Keep compatibility carefully at call sites that still pass booleans today.

**Verification:**
Run:

```bash
python3 -m py_compile views/main_window.py main.py
```

---

## Task 7: Replace Timer-Only Visual Logic with Sensor-Confirmed State

**Files:**
* Modify: `main.py`

**Implementation:**
Adjust the existing 90-second close timer:

* The timer may still send the closing pulse.
* UI should no longer assume the gate is closed immediately after the timer fires.
* After the closing pulse, wait for sensor-confirmed state.
* If state remains `EM_ANDAMENTO`, hand off to watchdog retry logic.
* If state reaches `FECHADO`, clear any pending open visual/command state.

**Verification:**
Run the app in mock/headless mode and simulate:

* Authorized tag -> pulse -> `ABERTO`.
* Timer fires -> pulse -> `FECHADO`.
* Timer fires -> pulse -> `EM_ANDAMENTO` -> retries -> `TRAVADO`.

---

## Task 8: Add Access Passage Reconciliation Skeleton

**Files:**
* Modify or create model/repository only if persistence is chosen.
* Otherwise modify: `main.py`

**Implementation:**
Because the physical passage sensor is still an open item, implement only a small internal skeleton:

* Create access event state names:
  * `AGUARDANDO_PASSAGEM`
  * `PASSAGEM_CONFIRMADA`
  * `PASSAGEM_NAO_CONFIRMADA`
* On authorized tag, mark the event as awaiting passage in logs or memory.
* Add a clearly isolated placeholder for future passage sensor callback.
* Do not pretend RFID alone confirms passage.

**Verification:**
Confirm authorized tag logs the pending passage state without breaking existing access log behavior.

---

## Task 9: Add Integration Tests for Watchdog Decisions

**Files:**
* Create: `tests/test_gate_watchdog.py`

**Implementation:**
Test the orchestration logic with fake gate controller and fake monitor:

* Access command reaches `ABERTO` after one pulse.
* Access command reads `FECHADO` and sends a second pulse to re-open.
* `EM_ANDAMENTO` retries up to `GATE_MAX_RETRY_ATTEMPTS`.
* Retry limit marks `TRAVADO`.
* External movement does not trigger retry.

If `main.py` remains too hard to test directly, extract a small pure-Python coordinator class first, for example `commands/gate_operation_coordinator.py`.

**Verification:**
Run:

```bash
pytest tests/test_gate_state_monitor.py tests/test_gate_watchdog.py
```

---

## Task 10: Manual Hardware Validation

**Files:**
* No code changes expected.

**Procedure:**
On the Raspberry Pi:

1. Confirm sensor voltage and electrical interface before connecting GPIO.
2. Start with `MOCK_HARDWARE=false`.
3. Validate each truth-table combination with magnets.
4. Measure real gate travel time and tune `GATE_PULSE_RESPONSE_SECONDS`.
5. Validate authorized access open flow.
6. Validate timer-triggered close flow.
7. Trigger manual remote movement and confirm it is logged as external movement.
8. Simulate a stuck/intermediate state and confirm retry limit reaches `TRAVADO`.

**Expected Result:**
The UI and logs reflect physical state from sensors, not timer assumptions.

---

## Suggested Implementation Order

1. Config constants.
2. `GateStateMonitor`.
3. Unit tests for truth table.
4. UI state API update.
5. Gate operation coordinator/watchdog.
6. `main.py` integration.
7. External movement logging.
8. Passage reconciliation skeleton.
9. Hardware validation.

## Open Decisions Before Final Hardware Deployment

* Confirm sensor supply voltage and GPIO isolation.
* Confirm final GPIO pins for both sensors.
* Confirm central gate input is truly single-pulse/toggle.
* Confirm whether a dry-contact relay is needed between Raspberry Pi and gate central.
* Measure real travel time and adjust timeouts.
* Choose passage sensor hardware.
* Decide whether passage and gate-state events should be persisted in SQLite.
