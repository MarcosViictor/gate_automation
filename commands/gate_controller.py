from __future__ import annotations
import threading
import logging
import time

import config
from commands.ultrasonic_sensor import UltrasonicSensor

logger = logging.getLogger(__name__)


class GateController:
    def __init__(self):
        self._lock = threading.Lock()
        self._gpio_ready = False

        if not config.MOCK_HARDWARE:
            self._setup_gpio()

        self._ultrasonic_sensor = (
            UltrasonicSensor() if config.ULTRASONIC_ENABLED else None
        )

    def open(self, duration: int = config.GATE_OPEN_DURATION):
        """Aciona o relé por `duration` segundos em thread separada."""
        thread = threading.Thread(
            target=self._pulse, args=(duration,), daemon=True
        )
        thread.start()

    def _pulse(self, duration: int):
        with self._lock:
            self._wait_until_clear_to_activate_relay()

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
            GPIO.setwarnings(False)
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
        GPIO = None
        relay_activated = False
        try:
            import RPi.GPIO as GPIO  # type: ignore
            # Configura como saída e envia sinal LOW (Fecha o circuito e liga o motor)
            GPIO.setup(config.GATE_RELAY_PIN, GPIO.OUT, initial=GPIO.LOW)
            relay_activated = True
            logger.info("Portão ABERTO (Sinal LOW na GPIO %d)", config.GATE_RELAY_PIN)
            time.sleep(duration)
        except Exception as exc:
            logger.error("Erro ao acionar GPIO: %s", exc)
        finally:
            if GPIO is not None and relay_activated:
                try:
                    # Volta para Entrada (Alta Impedância), cortando a fuga de corrente de 5V e desligando o relé
                    GPIO.setup(config.GATE_RELAY_PIN, GPIO.IN)
                    logger.info("Portão FECHADO (Alta Impedância na GPIO %d)", config.GATE_RELAY_PIN)
                except Exception as exc:
                    logger.error("Erro ao desligar relé GPIO: %s", exc)

    def _wait_until_clear_to_activate_relay(self):
        """Aguarda área livre antes de permitir o pulso do relé."""
        if not config.ULTRASONIC_ENABLED or self._ultrasonic_sensor is None:
            return

        blocked_since = time.monotonic()
        next_critical_at = blocked_since + config.ULTRASONIC_SAFETY_TIMEOUT

        while not self._ultrasonic_sensor.is_clear():
            now = time.monotonic()
            if now >= next_critical_at:
                logger.critical(
                    "Área obstruída há mais de %.0f segundo(s); relé não será acionado",
                    now - blocked_since,
                )
                next_critical_at += config.ULTRASONIC_SAFETY_TIMEOUT

            logger.info(
                "Área obstruída; relé aguardando liberação para acionar em %.1f segundo(s)",
                config.ULTRASONIC_RECHECK_INTERVAL,
            )
            time.sleep(config.ULTRASONIC_RECHECK_INTERVAL)

    def cleanup(self):
        """Libera os recursos GPIO ao encerrar o sistema."""
        if self._ultrasonic_sensor is not None:
            self._ultrasonic_sensor.cleanup()

        if not config.MOCK_HARDWARE and self._gpio_ready:
            try:
                import RPi.GPIO as GPIO  
                GPIO.cleanup(config.GATE_RELAY_PIN)
            except Exception:
                pass
