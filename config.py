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

# ==============================================================================
# Sensor Ultrassônico (JSN-SR04T) - validação de área livre antes de fechar
# ==============================================================================
ULTRASONIC_ENABLED = os.getenv("ULTRASONIC_ENABLED", "true").lower() == "true"

ULTRASONIC_TRIG_PIN = int(os.getenv("ULTRASONIC_TRIG_PIN", "23"))
ULTRASONIC_ECHO_PIN = int(os.getenv("ULTRASONIC_ECHO_PIN", "24"))

# Distância (cm) a partir da qual a área é considerada livre para fechar.
# ATENÇÃO: valor precisa ser calibrado em campo de acordo com a posição física do sensor.
ULTRASONIC_CLEAR_DISTANCE_CM = float(os.getenv("ULTRASONIC_CLEAR_DISTANCE_CM", "40.0"))

# Zona cega do sensor AJ-SR04M: leituras abaixo disso são inválidas.
ULTRASONIC_MIN_VALID_DISTANCE_CM = float(os.getenv("ULTRASONIC_MIN_VALID_DISTANCE_CM", "20.0"))

# Alcance máximo confiável do sensor: leituras acima disso são ruído/inválidas.
ULTRASONIC_MAX_VALID_DISTANCE_CM = float(os.getenv("ULTRASONIC_MAX_VALID_DISTANCE_CM", "450.0"))

# Intervalo entre re-checagens quando a área está obstruída, em segundos.
ULTRASONIC_RECHECK_INTERVAL = float(os.getenv("ULTRASONIC_RECHECK_INTERVAL", "3.0"))

# Intervalo entre disparos consecutivos dentro de uma mesma leitura.
ULTRASONIC_SAMPLE_INTERVAL = float(os.getenv("ULTRASONIC_SAMPLE_INTERVAL", "0.06"))

# Tempo máximo re-tentando antes de começar a logar alerta crítico periódico.
ULTRASONIC_SAFETY_TIMEOUT = float(os.getenv("ULTRASONIC_SAFETY_TIMEOUT", "300"))

# Timeout de uma leitura individual do sensor, quando suportado pela biblioteca.
ULTRASONIC_READ_TIMEOUT = float(os.getenv("ULTRASONIC_READ_TIMEOUT", "0.5"))

# Modo mock: "clear" simula área livre; "blocked" simula área obstruída.
MOCK_ULTRASONIC_STATE = os.getenv("MOCK_ULTRASONIC_STATE", "clear").lower()

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
