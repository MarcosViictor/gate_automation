# Design: Gate Timer and Auto-Close Adjustment

This document specifies the design for adjusting the gate opening/closing logic. Instead of a single impulse trigger representing an open/close cycle, the RFID tag reading triggers the gate opening, and a timer automatically triggers the gate closing after 1 minute and 30 seconds (90 seconds).

## Requirements & Constraints

1. **Auto-Close Timer**: Once a tag is read and authorized, the gate is pulsed to open. After exactly 90 seconds, the gate must receive a second pulse to close.
2. **Timer Reset (De-duplication & Extensions)**: If a new authorized tag is read while the timer is running:
   - The current close timer is cancelled.
   - A new close timer is started for another 90 seconds.
   - No new open impulse is sent (to avoid toggling the gate motor and stopping/closing it prematurely).
3. **Preservation**: The original tag handling code should be commented out rather than deleted/overwritten directly.
4. **Environment Support**: Must support both graphical interactive mode (using Tkinter) and headless service mode.

## Proposed Changes

### [main.py](file:///home/victor/dev/gate_automation/main.py)

We will introduce two local state variables in `main()` to track and manage the closing timer:
- `gate_timer: threading.Timer | None = None`
- `gate_timer_lock: threading.Lock`

We will modify `handle_tag` to:
1. Comment out the original authorization and gate opening blocks.
2. If the access is authorized:
   - Under `gate_timer_lock`, check if `gate_timer` is not `None`.
   - If a timer exists: cancel it and clear it.
   - If no timer exists: trigger `gate.open()` to start opening the gate.
   - Initialize a new `threading.Timer(90.0, close_gate)` and start it.
3. Define the `close_gate` callback:
   - Call `gate.open()` (sends the second pulse to close).
   - Under `gate_timer_lock`, reset `gate_timer = None`.
   - Update UI status if `app` is running.
4. Clean up in the `finally` block:
   - Cancel the `gate_timer` if it is still active when the program exits.

## Verification Plan

### Manual Verification
1. Run `python3 main.py` in mock mode.
2. Simulate reading a tag (e.g. `IN:01E28069150000401D63E8C9`).
3. Verify that:
   - UI status updates to "PORTÃO ABERTO".
   - The log shows "Enviando impulso para ABRIR o portão."
4. Simulate reading another tag 30 seconds later:
   - Verify that the log shows "Reiniciando o temporizador de 1:30 para fechar o portão."
   - Verify that the gate does not receive another open pulse.
5. Wait for 90 seconds from the second read:
   - Verify that the log shows "Temporizador expirou. Enviando impulso para FECHAR o portão."
   - Verify that the UI status returns to "PORTÃO FECHADO".
