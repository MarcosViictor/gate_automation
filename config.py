import os

# ==============================================================================
# Caminhos
# ==============================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "gate_local.db")

# ==============================================================================
# Servidor local (sincronização)
# ==============================================================================
SERVER_BASE_URL = os.getenv("SERVER_BASE_URL", "http://sitiobarreiras.app.br:55432")
SERVER_TIMEOUT = 5  # segundos
SYNC_INTERVAL = 300  # 5 minutos em segundos

# ==============================================================================
# Hardware – GPIO (Raspberry Pi)
# Defina MOCK_HARDWARE=True para rodar em um PC sem GPIO
# ==============================================================================
MOCK_HARDWARE = os.getenv("MOCK_HARDWARE", "false").lower() == "true"
SEED_TEST_DATA = os.getenv(
	"SEED_TEST_DATA",
	"true" if MOCK_HARDWARE else "false",
).lower() == "true"

GATE_RELAY_PIN = 18        # GPIO para acionar o relé do portão
GATE_OPEN_DURATION = 5     # Tempo em segundos que o portão fica aberto

# Sensores Hall
GATE_SENSOR_A_PIN = int(os.getenv("GATE_SENSOR_A_PIN", "17"))
GATE_SENSOR_B_PIN = int(os.getenv("GATE_SENSOR_B_PIN", "27"))

# Tempos e Watchdog
GATE_STATE_POLL_INTERVAL = float(os.getenv("GATE_STATE_POLL_INTERVAL", "0.05"))
GATE_STATE_DEBOUNCE_SECONDS = float(os.getenv("GATE_STATE_DEBOUNCE_SECONDS", "0.02"))
GATE_MOVING_TIMEOUT_SECONDS = float(os.getenv("GATE_MOVING_TIMEOUT_SECONDS", "30.0"))
GATE_PULSE_RESPONSE_SECONDS = float(os.getenv("GATE_PULSE_RESPONSE_SECONDS", "10.0"))
GATE_RETRY_COOLDOWN_SECONDS = float(os.getenv("GATE_RETRY_COOLDOWN_SECONDS", "2.0"))
GATE_MAX_RETRY_ATTEMPTS = int(os.getenv("GATE_MAX_RETRY_ATTEMPTS", "3"))
GATE_PASSAGE_CONFIRMATION_SECONDS = float(os.getenv("GATE_PASSAGE_CONFIRMATION_SECONDS", "30.0"))

RFID_PORT_IN = os.getenv("RFID_PORT_IN", "/dev/ttyUSB0")    # Porta serial Entrada
RFID_PORT_OUT = os.getenv("RFID_PORT_OUT", "/dev/ttyUSB1")  # Porta serial Saída
RFID_BAUDRATE = 9600
RFID_MODE = os.getenv("RFID_MODE", "hid").lower()  # "serial" | "hid" | "auto"

# Configurações para leitores HID (modo "hid")
RFID_HID_VENDOR_ID = os.getenv("RFID_HID_VENDOR_ID", "0x1A86")  # ex.: 0x1A86
RFID_HID_PRODUCT_ID = os.getenv("RFID_HID_PRODUCT_ID", "0xE010")  # ex.: 0xE010
RFID_HID_PACKET_SIZE = int(os.getenv("RFID_HID_PACKET_SIZE", "64"))
RFID_HID_OFFSET = int(os.getenv("RFID_HID_OFFSET", "18"))
RFID_HID_STRIP_HEX_DIGITS = int(os.getenv("RFID_HID_STRIP_HEX_DIGITS", "6"))
RFID_HID_INTERFACE_NUMBER = os.getenv("RFID_HID_INTERFACE_NUMBER", "")
RFID_HID_USAGE_PAGE = os.getenv("RFID_HID_USAGE_PAGE", "")
RFID_HID_USAGE = os.getenv("RFID_HID_USAGE", "")
RFID_HID_INTERFACE_IDLE_SECONDS = float(os.getenv("RFID_HID_INTERFACE_IDLE_SECONDS", "4.0"))
RFID_HID_LOG_ENUMERATION = os.getenv("RFID_HID_LOG_ENUMERATION", "true").lower() == "true"

# Controle de polling e redução de leituras duplicadas
RFID_POLL_INTERVAL = float(os.getenv("RFID_POLL_INTERVAL", "0.05"))
RFID_DEDUP_SECONDS = float(os.getenv("RFID_DEDUP_SECONDS", "0.30"))
