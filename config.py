import os
from dotenv import load_dotenv, set_key

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(ENV_FILE_PATH)

def update_env(key: str, value: str):
    if not os.path.exists(ENV_FILE_PATH):
        open(ENV_FILE_PATH, 'a').close()
    set_key(ENV_FILE_PATH, key, value)
    os.environ[key] = value
# ==============================================================================
# Servidor local (sb-gatehouse)
# ==============================================================================
SERVER_HOST = os.getenv("SERVER_HOST", "localhost")
SERVER_PORT = os.getenv("SERVER_PORT", "8001")
SERVER_TIMEOUT = int(os.getenv("SERVER_TIMEOUT", "5"))  # segundos
ACCESS_PATH = "/api/raspberry/access"  # rota fixa do endpoint de validação


def get_server_base_url() -> str:
    """Monta a base URL lendo host/porta do ambiente a cada chamada,
    para que mudanças salvas pela GUI valham sem reiniciar."""
    host = os.getenv("SERVER_HOST", SERVER_HOST)
    port = os.getenv("SERVER_PORT", SERVER_PORT)
    return f"http://{host}:{port}"


SYNC_INTERVAL = 300  # 5 minutos em segundos

# ==============================================================================
# Hardware – GPIO (Raspberry Pi)
# Defina MOCK_HARDWARE=True para rodar em um PC sem GPIO
# ==============================================================================
MOCK_HARDWARE = os.getenv("MOCK_HARDWARE", "false").lower() == "true"

GATE_RELAY_PIN = 18        # GPIO para acionar o relé do portão
GATE_OPEN_DURATION = 5     # Tempo em segundos que o portão fica aberto

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

# ==============================================================================
# Sensor Ultrassônico (JSN-SR04T)
# ==============================================================================
ULTRASONIC_TRIGGER_PIN = int(os.getenv("ULTRASONIC_TRIGGER_PIN", "23"))
ULTRASONIC_ECHO_PIN = int(os.getenv("ULTRASONIC_ECHO_PIN", "24"))
ULTRASONIC_PRESENCE_THRESHOLD = float(os.getenv("ULTRASONIC_PRESENCE_THRESHOLD", "1.5")) # metros
GATE_SAFE_CLOSE_DELAY = int(os.getenv("GATE_SAFE_CLOSE_DELAY", "3")) # segundos
GATE_FALLBACK_TIMEOUT = int(os.getenv("GATE_FALLBACK_TIMEOUT", "120")) # segundos
