# Design: Raspberry Pi Auto-start Setup

This document outlines the design for configuring the Gate Automation system to run automatically on Raspberry Pi boot.

## Goal

Run the Gate Automation application in headless mode automatically when the Raspberry Pi boots, ensuring it runs with root permissions (to access serial/USB RFID reader and GPIO pins) and restarts automatically if it crashes.

## Design Details

### 1. Systemd Service

We will configure a systemd service under `/etc/systemd/system/gate_automation.service`.

- **User**: `root` (required for direct access to USB HID/serial readers and Raspberry Pi GPIO pins).
- **WorkingDirectory**: `/opt/gate_automation`
- **ExecStart**: `/opt/gate_automation/venv/bin/python main.py`
  - Running Python inside the virtual environment directory directly uses the installed packages without needing to run `source venv/bin/activate` in bash.
- **Environment Variables**:
  - `HEADLESS=true`: Runs without the Tkinter GUI.
  - `MOCK_HARDWARE=false`: Interfaces with real RFID readers and GPIO.
  - `RFID_MODE=hid`: Default RFID reading mode.
  - `RFID_HID_VENDOR_ID=0x1A86`
  - `RFID_HID_PRODUCT_ID=0xE010`
  - `RFID_HID_OFFSET=18`
  - `RFID_HID_STRIP_HEX_DIGITS=6`
- **EnvironmentFile**: `- /opt/gate_automation/.env` (optional local environment file to override values).
- **Restart**: `always` (restarts the service if it exits or crashes, with a 5-second delay).

### 2. Install Script

We will provide an `install_service.sh` script to:
1. Copy `gate_automation.service` to `/etc/systemd/system/`.
2. Reload systemd daemon config (`systemctl daemon-reload`).
3. Enable the service to start on boot (`systemctl enable gate_automation.service`).
4. Start the service immediately (`systemctl start gate_automation.service`).

## Alternatives Considered

- **Cron `@reboot`**: Easy but lacks status checking (`systemctl status`), auto-restart on crashes, and native logging integrations.
- **`/etc/rc.local`**: Deprecated, harder to manage and debug.
