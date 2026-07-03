from __future__ import annotations

import logging
import time

import config
from commands.ultrasonic_sensor import UltrasonicSensor


def main():
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    sensor = UltrasonicSensor()
    print("Teste real do sensor ultrassônico", flush=True)
    print(f"MOCK_HARDWARE={config.MOCK_HARDWARE}", flush=True)
    print(f"ULTRASONIC_ENABLED={config.ULTRASONIC_ENABLED}", flush=True)
    print(f"Trigger GPIO={config.ULTRASONIC_TRIG_PIN}", flush=True)
    print(f"Echo GPIO={config.ULTRASONIC_ECHO_PIN}", flush=True)
    print(f"Distância livre >= {config.ULTRASONIC_CLEAR_DISTANCE_CM:.1f} cm", flush=True)
    print("Pressione Ctrl+C para encerrar.", flush=True)

    try:
        while True:
            if config.MOCK_HARDWARE:
                is_clear = sensor.is_clear()
                state = "LIVRE" if is_clear else "OBSTRUÍDO"
                print(f"[MOCK] Estado: {state}", flush=True)
            else:
                distance_cm = sensor.measure_distance_cm()
                is_clear = (
                    distance_cm is not None
                    and distance_cm >= config.ULTRASONIC_CLEAR_DISTANCE_CM
                )

                if distance_cm is None:
                    print("Leitura inválida | estado: OBSTRUÍDO/INSEGURO", flush=True)
                else:
                    state = "LIVRE" if is_clear else "OBSTRUÍDO"
                    print(f"Distância: {distance_cm:.1f} cm | estado: {state}", flush=True)

            time.sleep(config.ULTRASONIC_RECHECK_INTERVAL)
    except KeyboardInterrupt:
        print("\nTeste encerrado.", flush=True)
    finally:
        sensor.cleanup()


if __name__ == "__main__":
    main()
