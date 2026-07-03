from __future__ import annotations

import inspect
import logging
import statistics
import time
from typing import Optional

import config

logger = logging.getLogger(__name__)


class UltrasonicSensor:
    """Mede distância e valida se a área do portão está livre."""

    def __init__(self):
        self._sensor = None
        self._last_clear_state: Optional[bool] = None

        if config.MOCK_HARDWARE:
            logger.info("[MOCK] Sensor ultrassônico inicializado em modo simulado")
            return

        try:
            from gpiozero import DistanceSensor

            kwargs = {
                "echo": config.ULTRASONIC_ECHO_PIN,
                "trigger": config.ULTRASONIC_TRIG_PIN,
                "max_distance": config.ULTRASONIC_MAX_VALID_DISTANCE_CM / 100,
                "queue_len": 1,
            }
            if "timeout" in inspect.signature(DistanceSensor).parameters:
                kwargs["timeout"] = config.ULTRASONIC_READ_TIMEOUT

            self._sensor = DistanceSensor(**kwargs)
            logger.info(
                "Sensor ultrassônico configurado (trigger GPIO %d, echo GPIO %d)",
                config.ULTRASONIC_TRIG_PIN,
                config.ULTRASONIC_ECHO_PIN,
            )
        except ImportError:
            logger.error("gpiozero não disponível. Instale com: pip install gpiozero")
        except Exception as exc:
            logger.error("Erro ao configurar sensor ultrassônico: %s", exc)

    def _read_single_cm(self) -> Optional[float]:
        if self._sensor is None:
            return None

        try:
            distance_cm = float(self._sensor.distance) * 100
        except Exception as exc:
            logger.debug("Falha ao ler sensor ultrassônico: %s", exc)
            return None

        if distance_cm < config.ULTRASONIC_MIN_VALID_DISTANCE_CM:
            logger.debug(
                "Leitura ultrassônica inválida: %.1f cm abaixo da zona mínima",
                distance_cm,
            )
            return None

        if distance_cm > config.ULTRASONIC_MAX_VALID_DISTANCE_CM:
            logger.debug(
                "Leitura ultrassônica inválida: %.1f cm acima do alcance máximo",
                distance_cm,
            )
            return None

        logger.debug("Leitura ultrassônica: %.1f cm", distance_cm)
        return distance_cm

    def measure_distance_cm(self) -> Optional[float]:
        readings = []

        for index in range(5):
            distance_cm = self._read_single_cm()
            if distance_cm is not None:
                readings.append(distance_cm)

            if index < 4:
                time.sleep(config.ULTRASONIC_SAMPLE_INTERVAL)

        if not readings:
            logger.debug("Nenhuma leitura ultrassônica válida")
            return None

        median_cm = float(statistics.median(readings))
        logger.debug("Mediana ultrassônica: %.1f cm", median_cm)
        return median_cm

    def is_clear(self) -> bool:
        if config.MOCK_HARDWARE:
            is_clear = config.MOCK_ULTRASONIC_STATE == "clear"
            logger.debug(
                "[MOCK] Sensor ultrassônico: %s",
                "livre" if is_clear else "obstruído",
            )
            self._log_state_change(is_clear)
            return is_clear

        distance_cm = self.measure_distance_cm()
        is_clear = (
            distance_cm is not None
            and distance_cm >= config.ULTRASONIC_CLEAR_DISTANCE_CM
        )
        self._log_state_change(is_clear)
        return is_clear

    def cleanup(self):
        """Libera os recursos do sensor ultrassônico."""
        if self._sensor is None:
            return

        try:
            self._sensor.close()
        except Exception as exc:
            logger.debug("Erro ao liberar sensor ultrassônico: %s", exc)

    def _log_state_change(self, is_clear: bool):
        if self._last_clear_state is is_clear:
            return

        logger.info(
            "Área de passagem %s pelo sensor ultrassônico",
            "livre" if is_clear else "obstruída",
        )
        self._last_clear_state = is_clear
