import config
import logging
import threading
import time

logger = logging.getLogger(__name__)

class UltrasonicSensor:
    def __init__(self):
        self._distance = 9.9
        self._ready = False
        if not config.MOCK_HARDWARE:
            self._setup_gpio()
            
    def _setup_gpio(self):
        pass # Will implement in next tasks for real hardware

    def is_vehicle_present(self) -> bool:
        if config.MOCK_HARDWARE:
            return False # For now, mock always says no vehicle
        return self._distance < config.ULTRASONIC_PRESENCE_THRESHOLD
