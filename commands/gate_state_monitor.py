import threading
import logging
import time
from typing import Callable, Optional, Tuple

import config

logger = logging.getLogger(__name__)

GATE_OPEN = "ABERTO"
GATE_CLOSED = "FECHADO"
GATE_MOVING = "EM_ANDAMENTO"
GATE_STUCK = "TRAVADO"

class GateStateMonitor:
    """
    Monitor do estado físico do portão usando 2 sensores Hall NPN.
    Tabela verdade:
    - Sensor A: Ativo (LOW), Sensor B: Inativo (HIGH) -> ABERTO
    - Sensor A: Inativo (HIGH), Sensor B: Ativo (LOW) -> ABERTO
    - Sensor A: Ativo (LOW), Sensor B: Ativo (LOW) -> FECHADO
    - Sensor A: Inativo (HIGH), Sensor B: Inativo (HIGH) -> EM_ANDAMENTO
    """

    def __init__(self, on_state_change: Optional[Callable[[str], None]] = None):
        self._on_state_change = on_state_change
        self._state = GATE_MOVING
        self._running = False
        self._thread = None
        self._mock_state = GATE_MOVING

        if not config.MOCK_HARDWARE:
            self._setup_gpio()

    def _setup_gpio(self):
        try:
            import RPi.GPIO as GPIO
            GPIO.setmode(GPIO.BCM)
            # Pull-up interno conforme a spec
            GPIO.setup(config.GATE_SENSOR_A_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.setup(config.GATE_SENSOR_B_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            logger.info("GPIO para sensores Hall configurada (A=%d, B=%d)", 
                        config.GATE_SENSOR_A_PIN, config.GATE_SENSOR_B_PIN)
        except ImportError:
            logger.error("RPi.GPIO não disponível. Usando lógica de mock internamente.")
        except Exception as exc:
            logger.error("Erro ao configurar GPIO dos sensores: %s", exc)

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()
        logger.info("Monitor do estado físico do portão iniciado.")

    def stop(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        logger.info("Monitor do estado físico do portão parado.")

    def get_state(self) -> str:
        return self._state

    def set_mock_state(self, state: str) -> None:
        if state not in [GATE_OPEN, GATE_CLOSED, GATE_MOVING, GATE_STUCK]:
            raise ValueError(f"Estado inválido: {state}")
        self._mock_state = state
        # In mock mode, force immediate state evaluation to avoid waiting for poll loop
        # in some synchronous unit tests if needed, though poll loop will pick it up
        if config.MOCK_HARDWARE and not self._running:
            self._state = self._mock_state

    def _read_sensors(self) -> Tuple[int, int]:
        if config.MOCK_HARDWARE:
            if self._mock_state == GATE_OPEN:
                return (0, 1)  # LOW, HIGH
            elif self._mock_state == GATE_CLOSED:
                return (0, 0)  # LOW, LOW
            elif self._mock_state == GATE_MOVING:
                return (1, 1)  # HIGH, HIGH
            elif self._mock_state == GATE_STUCK:
                # Tratado como moving do ponto de vista de sensor, e travado pela logica watchdog
                return (1, 1)
            return (1, 1)
        
        try:
            import RPi.GPIO as GPIO
            val_a = GPIO.input(config.GATE_SENSOR_A_PIN)
            val_b = GPIO.input(config.GATE_SENSOR_B_PIN)
            return (val_a, val_b)
        except Exception as exc:
            logger.error("Erro ao ler GPIO dos sensores: %s", exc)
            return (1, 1) # Falha na leitura, assume aberto/movimento solto (high)

    def _map_state(self, val_a: int, val_b: int) -> str:
        if val_a == 0 and val_b == 1:
            return GATE_OPEN
        elif val_a == 1 and val_b == 0:
            return GATE_OPEN
        elif val_a == 0 and val_b == 0:
            return GATE_CLOSED
        else: # val_a == 1 and val_b == 1
            return GATE_MOVING

    def _poll_loop(self):
        last_moving_start = None
        
        while self._running:
            try:
                # Leitura inicial
                val_a1, val_b1 = self._read_sensors()
                
                # Debounce
                time.sleep(config.GATE_STATE_DEBOUNCE_SECONDS)
                
                # Leitura secundária
                val_a2, val_b2 = self._read_sensors()
                
                # Só aceita se estabilizou
                if val_a1 == val_a2 and val_b1 == val_b2:
                    new_state = self._map_state(val_a1, val_b1)
                    
                    if new_state != self._state:
                        self._state = new_state
                        logger.info("Estado físico do portão alterado: %s", self._state)
                        
                        if self._on_state_change:
                            self._on_state_change(self._state)
                            
                        if new_state == GATE_MOVING:
                            last_moving_start = time.time()
                        else:
                            last_moving_start = None
                            
                    elif new_state == GATE_MOVING and last_moving_start is not None:
                        # Verifica timeout de movimento contínuo
                        if time.time() - last_moving_start > config.GATE_MOVING_TIMEOUT_SECONDS:
                            logger.warning("Portão permaneceu EM_ANDAMENTO por mais de %.1f segundos", 
                                           config.GATE_MOVING_TIMEOUT_SECONDS)
                            # Não alteramos pra travado aqui, quem cuida do TRAVADO é o watchdog de comandos,
                            # mas resetamos o timer para não floodar o log
                            last_moving_start = time.time()
            except Exception as e:
                logger.error("Erro no polling dos sensores do portão: %s", e)
                
            time.sleep(config.GATE_STATE_POLL_INTERVAL)
