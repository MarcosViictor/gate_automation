# Dual Reader Integration Design

## Overview
The goal is to support two RFID readers (IN and OUT) to properly record vehicle direction in the access logs. Both readers will trigger the same physical gate mechanism, leveraging the recently implemented Ultrasonic Sensor for active closing.

## Proposed Approach
1. **Uncomment Secondary Reader**: In `main.py`, uncomment the lines that initialize and start the `reader_out` instance using the `RFID_PORT_OUT` configuration.
2. **Reuse the existing callback**: The existing `handle_tag(tag_code, direction)` method already accepts the `direction` parameter and passes it to `auth.process()`. The IN reader passes "IN" and the OUT reader passes "OUT".
3. **Migrate to Active Close**: Replace the static 90-second timer inside `handle_tag` with the new `gate._pulse_active_close()` method. Since `_pulse_active_close` blocks while waiting for the vehicle, it should be called in a background thread to prevent blocking the `handle_tag` thread or the UI.

## Components to Modify
- `main.py`:
  - Uncomment `reader_out` setup.
  - Refactor `handle_tag` to spawn a new thread running `gate._pulse_active_close()` when access is authorized.
  - Remove the old `threading.Timer` 90-second logic.

## Trade-offs
- Calling `_pulse_active_close` blocks until the vehicle passes or a timeout occurs. Running it in a background thread ensures the RFID reader can still process other tags or UI updates. However, we must ensure multiple overlapping reads do not trigger multiple concurrent gate opening threads (adding a lock or a simple boolean flag in `main.py`).
