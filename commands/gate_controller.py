from __future__ import annotations
import threading
import logging
import time

import config

logger = logging.getLogger(__name__)


class GateController:
    def __init__(self, sensor=None):
        self._lock = threading.Lock()
        self._gpio_ready = False
        self.sensor = sensor

        if not config.MOCK_HARDWARE:
            self._setup_gpio()

    def open(self, duration: int = config.GATE_OPEN_DURATION):
        """Aciona o relé por `duration` segundos em thread separada."""
        thread = threading.Thread(
            target=self._pulse, args=(duration,), daemon=True
        )
        thread.start()

    def _pulse(self, duration: int):
        with self._lock:
            if config.MOCK_HARDWARE:
                logger.info("[MOCK] Portão ABERTO por %d segundo(s)", duration)
                time.sleep(duration)
                logger.info("[MOCK] Portão FECHADO")
            else:
                self._gpio_open(duration)

    def _setup_gpio(self):
        try:
            import RPi.GPIO as GPIO  
            GPIO.setmode(GPIO.BCM)
            # Como o relé é 5V e o Raspberry é 3.3V, usamos GPIO.IN (Alta Impedância) para o estado desligado.
            GPIO.setup(config.GATE_RELAY_PIN, GPIO.IN)
            self._gpio_ready = True
            logger.info("GPIO configurado no pino %d (Hack Alta Impedância 5V)", config.GATE_RELAY_PIN)
        except ImportError:
            logger.error("RPi.GPIO não disponível. Instale no Raspberry Pi.")
        except Exception as exc:
            logger.error("Erro ao configurar GPIO: %s", exc)

    def _gpio_open(self, duration: int):
        if not self._gpio_ready:
            logger.error("GPIO não inicializado – portão não acionado")
            return
        try:
            import RPi.GPIO as GPIO  # type: ignore
            # Configura como saída e envia sinal LOW (Fecha o circuito e liga o motor)
            GPIO.setup(config.GATE_RELAY_PIN, GPIO.OUT, initial=GPIO.LOW)
            logger.info("Portão ABERTO (Sinal LOW na GPIO %d)", config.GATE_RELAY_PIN)
            time.sleep(duration)
            # Volta para Entrada (Alta Impedância), cortando a fuga de corrente de 5V e desligando o relé
            GPIO.setup(config.GATE_RELAY_PIN, GPIO.IN)
            logger.info("Portão FECHADO (Alta Impedância na GPIO %d)", config.GATE_RELAY_PIN)
        except Exception as exc:
            logger.error("Erro ao acionar GPIO: %s", exc)

    def _pulse_active_close(self):
        if config.MOCK_HARDWARE:
            logger.info("[MOCK] Portão ABERTO (Fechamento Ativo)")
        else:
            self._gpio_open_cmd()

        # Phase 1: Wait for vehicle to arrive
        timeout = time.time() + config.GATE_FALLBACK_TIMEOUT
        vehicle_arrived = False
        while time.time() < timeout:
            if self.sensor and self.sensor.is_vehicle_present():
                vehicle_arrived = True
                break
            time.sleep(0.5)

        # Phase 2: Wait for vehicle to pass completely
        if vehicle_arrived:
            logger.info("Veículo detectado. Aguardando passagem...")
            while self.sensor and self.sensor.is_vehicle_present():
                time.sleep(0.5)
            logger.info("Passagem concluída. Aguardando safe delay...")
            time.sleep(config.GATE_SAFE_CLOSE_DELAY)
        else:
            logger.info("Timeout de fallback atingido. Nenhum veículo passou.")

        if config.MOCK_HARDWARE:
            logger.info("[MOCK] Portão FECHADO (Fechamento Ativo)")
        else:
            self._gpio_close_cmd()

    def _gpio_open_cmd(self):
        if not self._gpio_ready: return
        import RPi.GPIO as GPIO  # type: ignore
        GPIO.setup(config.GATE_RELAY_PIN, GPIO.OUT, initial=GPIO.LOW)

    def _gpio_close_cmd(self):
        if not self._gpio_ready: return
        import RPi.GPIO as GPIO  # type: ignore
        GPIO.setup(config.GATE_RELAY_PIN, GPIO.IN)

    def cleanup(self):
        """Libera os recursos GPIO ao encerrar o sistema."""
        if not config.MOCK_HARDWARE and self._gpio_ready:
            try:
                import RPi.GPIO as GPIO  
                GPIO.cleanup()
            except Exception:
                pass
