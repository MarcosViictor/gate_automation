#!/bin/bash

cd /opt/gate_automation

source venv/bin/activate

export HEADLESS=true
export MOCK_HARDWARE=false
export RFID_MODE=hid
export RFID_HID_VENDOR_ID=0x1A86
export RFID_HID_PRODUCT_ID=0xE010
export RFID_HID_OFFSET=18
export RFID_HID_STRIP_HEX_DIGITS=4

echo "Iniciando Gate Automation em modo HEADLESS..."

exec python3 main.py
