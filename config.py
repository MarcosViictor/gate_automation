import os

# ==============================================================================
# Caminhos
# ==============================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "gate_local.db")

# ==============================================================================
# Servidor local (sincronização)
# ==============================================================================
SERVER_BASE_URL = os.getenv("SERVER_BASE_URL", "http://192.168.1.100:8000")
SERVER_TIMEOUT = 5  # segundos
SYNC_INTERVAL = 300  # 5 minutos em segundos

# ==============================================================================
# Hardware – GPIO (Raspberry Pi)
# Defina MOCK_HARDWARE=True para rodar em um PC sem GPIO
# ==============================================================================
MOCK_HARDWARE = os.getenv("MOCK_HARDWARE", "false").lower() == "true"

GATE_RELAY_PIN = 18        # GPIO para acionar o relé do portão
GATE_OPEN_DURATION = 5     # Tempo em segundos que o portão fica aberto

RFID_PORT = os.getenv("RFID_PORT", "/dev/ttyUSB0")  # Porta serial do leitor RFID
RFID_BAUDRATE = 9600
RFID_MODE = os.getenv("RFID_MODE", "auto").lower()  # "serial" | "hid" | "auto"

# Configurações para leitores HID (modo "hid")
RFID_HID_VENDOR_ID = os.getenv("RFID_HID_VENDOR_ID", "")  # ex.: 0x1234
RFID_HID_PRODUCT_ID = os.getenv("RFID_HID_PRODUCT_ID", "")  # ex.: 0x5678
RFID_HID_PACKET_SIZE = int(os.getenv("RFID_HID_PACKET_SIZE", "64"))
RFID_HID_OFFSET = int(os.getenv("RFID_HID_OFFSET", "18"))
RFID_HID_STRIP_HEX_DIGITS = int(os.getenv("RFID_HID_STRIP_HEX_DIGITS", "4"))

# Controle de polling e redução de leituras duplicadas
RFID_POLL_INTERVAL = float(os.getenv("RFID_POLL_INTERVAL", "0.05"))
RFID_DEDUP_SECONDS = float(os.getenv("RFID_DEDUP_SECONDS", "0.30"))

# ==============================================================================
# Interface
# ==============================================================================
APP_TITLE = "Gate Automation"
APP_GEOMETRY = "900x600"
THEME = "dark"   # "dark" | "light" | "system"
COLOR_SCHEME = "blue"
