from __future__ import annotations
import threading
import logging
import time

import config

logger = logging.getLogger(__name__)


class GateController:
    """
    Controla o relé físico que aciona o portão.

    Em modo MOCK apenas loga o comando – sem GPIO real.
    Em produção usa RPi.GPIO para pulsar o pino configurado.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._gpio_ready = False

        if not config.MOCK_HARDWARE:
            self._setup_gpio()

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------
    def open(self, duration: int = config.GATE_OPEN_DURATION):
        """Aciona o relé por `duration` segundos em thread separada."""
        thread = threading.Thread(
            target=self._pulse, args=(duration,), daemon=True
        )
        thread.start()

    # ------------------------------------------------------------------
    # Implementação
    # ------------------------------------------------------------------
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
            import RPi.GPIO as GPIO  # type: ignore
            GPIO.setmode(GPIO.BCM)
            # A maioria dos módulos de relé é Active-Low. O estado desligado é HIGH.
            GPIO.setup(config.GATE_RELAY_PIN, GPIO.OUT, initial=GPIO.HIGH)
            self._gpio_ready = True
            logger.info("GPIO configurado no pino %d (Lógica Active-Low)", config.GATE_RELAY_PIN)
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
            # Em relés Active-Low, enviar LOW fecha o circuito (liga o motor)
            GPIO.output(config.GATE_RELAY_PIN, GPIO.LOW)
            logger.info("Portão ABERTO (Sinal LOW na GPIO %d)", config.GATE_RELAY_PIN)
            time.sleep(duration)
            # Voltar para HIGH abre o circuito (desliga o motor)
            GPIO.output(config.GATE_RELAY_PIN, GPIO.HIGH)
            logger.info("Portão FECHADO (Sinal HIGH na GPIO %d)", config.GATE_RELAY_PIN)
        except Exception as exc:
            logger.error("Erro ao acionar GPIO: %s", exc)

    def cleanup(self):
        """Libera os recursos GPIO ao encerrar o sistema."""
        if not config.MOCK_HARDWARE and self._gpio_ready:
            try:
                import RPi.GPIO as GPIO  # type: ignore
                GPIO.cleanup()
            except Exception:
                pass
