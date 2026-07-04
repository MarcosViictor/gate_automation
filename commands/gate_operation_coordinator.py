import threading
import time
import logging
from typing import Callable, Optional

import config
from commands.gate_state_monitor import GateStateMonitor, GATE_OPEN, GATE_CLOSED, GATE_MOVING, GATE_STUCK
from commands.gate_controller import GateController

logger = logging.getLogger(__name__)

class GateOperationCoordinator:
    def __init__(self, controller: GateController, monitor: GateStateMonitor):
        self.controller = controller
        self.monitor = monitor
        
        self.comando_ativo_pelo_sistema = False
        self.active_intent = None
        self._lock = threading.Lock()
        
        self.on_state_update: Optional[Callable[[str], None]] = None

        # Redireciona o callback do monitor para a nossa lógica
        self._original_on_change = self.monitor._on_state_change
        self.monitor._on_state_change = self._handle_state_change

    def _handle_state_change(self, state: str):
        # Call the original change callback if any (useful for testing or other integrations)
        if self._original_on_change:
            self._original_on_change(state)

        # Notify UI/main loop
        if self.on_state_update:
            self.on_state_update(state)
            
        with self._lock:
            if not self.comando_ativo_pelo_sistema:
                logger.info("Movimento externo detectado. Estado atual: %s", state)

    def trigger_gate(self, intent: str = GATE_OPEN):
        """
        Trigger a gate pulse with a specific intent (GATE_OPEN or GATE_CLOSED).
        """
        threading.Thread(target=self._watchdog_flow, args=(intent,), daemon=True).start()

    def _watchdog_flow(self, intent: str):
        with self._lock:
            if self.comando_ativo_pelo_sistema:
                logger.warning("Comando já ativo. Ignorando novo gatilho.")
                return
            self.comando_ativo_pelo_sistema = True
            self.active_intent = intent
        
        retries = 0
        max_retries = config.GATE_MAX_RETRY_ATTEMPTS
        
        try:
            while retries <= max_retries:
                logger.info("Enviando pulso (intent=%s, tentativa=%d/%d)", intent, retries, max_retries)
                self.controller.open() # Envia o pulso de comando
                
                # Aguarda o tempo de resposta mecânica do portão
                time.sleep(config.GATE_PULSE_RESPONSE_SECONDS)
                
                current_state = self.monitor.get_state()
                
                if current_state == intent:
                    logger.info("Portão atingiu estado esperado: %s", intent)
                    break
                    
                if current_state == GATE_STUCK:
                    logger.error("Portão já se encontra TRAVADO. Abortando operação.")
                    break
                    
                # Estado não é o esperado: ou continua em andamento, ou foi pro lado errado (abriu quando devia fechar)
                retries += 1
                if retries <= max_retries:
                    logger.warning("Portão em estado inesperado (%s). Aguardando cooldown antes da retentativa.", current_state)
                    time.sleep(config.GATE_RETRY_COOLDOWN_SECONDS)
                else:
                    logger.error("Portão entrou em estado TRAVADO; intervencao manual necessaria")
                    if self.on_state_update:
                        self.on_state_update(GATE_STUCK)
                    break
        finally:
            with self._lock:
                self.comando_ativo_pelo_sistema = False
                self.active_intent = None
