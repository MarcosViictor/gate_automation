#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -d "venv" ]; then
    source venv/bin/activate
fi

export MOCK_HARDWARE="${MOCK_HARDWARE:-false}"
export RFID_MODE="${RFID_MODE:-hid}"
export RFID_HID_VENDOR_ID="${RFID_HID_VENDOR_ID:-0x1A86}"
export RFID_HID_PRODUCT_ID="${RFID_HID_PRODUCT_ID:-0xE010}"
export RFID_HID_OFFSET="${RFID_HID_OFFSET:-18}"
export RFID_HID_STRIP_HEX_DIGITS="${RFID_HID_STRIP_HEX_DIGITS:-4}"

if [ -z "$DISPLAY" ] && [ "$HEADLESS" != "true" ]; then
    echo "Nenhuma tela detectada (DISPLAY não configurado). O programa rodará em modo headless automaticamente."
fi
exec python3 main.py "$@"
