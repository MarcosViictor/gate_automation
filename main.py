"""Ponto de entrada — Gate Automation (thin client).

Lê tags RFID e valida em tempo real no servidor local (sb-gatehouse).
Config de servidor/portas vem do .env (editável pela GUI ou por SSH no Raspberry).

Variáveis de ambiente:
    HEADLESS=true        Força modo sem GUI (auto-detectado se não houver DISPLAY)
    MOCK_HARDWARE=true   Roda sem GPIO/serial (a GUI injeta tags manualmente)
"""
import os
import sys
import signal
import threading
import logging

import config
from controllers.auth_controller import AuthController
from commands.rfid_reader import RFIDReader
from commands.gate_controller import GateController

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    logger.info("Iniciando Gate Automation (thin client)...")

    headless = os.getenv("HEADLESS", "false").lower() == "true"
    if not headless and sys.platform.startswith("linux") and not os.getenv("DISPLAY"):
        logger.info("Sem DISPLAY no Linux; ativando modo headless automaticamente.")
        headless = True

    gate = GateController()
    auth = AuthController()

    app = None
    reader_in = None
    reader_out = None

    def handle_tag(tag_code: str, direction: str):
        logger.info("Leitura: Tag=%s, Direction=%s", tag_code, direction)
        result = auth.check(tag_code, direction)
        if result.authorized:
            logger.info("🔓 ACESSO AUTORIZADO para a tag %s", tag_code)
            gate.open()
        else:
            logger.warning("🔒 ACESSO NEGADO para a tag %s. Motivo: %s", tag_code, result.reason)
        if app:
            app.after(0, lambda: (
                app.add_read_row(result),
                app.update_gate_status(result.authorized),
                app.update_net_status(result.online),
            ))

    def start_readers(port_in: str, port_out: str):
        nonlocal reader_in, reader_out
        if reader_in:
            reader_in.stop()
        if reader_out:
            reader_out.stop()
        reader_in = RFIDReader("IN", port_in, handle_tag)
        reader_out = RFIDReader("OUT", port_out, handle_tag)
        reader_in.start()
        reader_out.start()

    def handle_save_config(cfg: dict):
        config.update_env("SERVER_HOST", cfg["server_host"])
        config.update_env("SERVER_PORT", cfg["server_port"])
        config.update_env("RFID_PORT_IN", cfg["rfid_port_in"])
        config.update_env("RFID_PORT_OUT", cfg["rfid_port_out"])
        start_readers(cfg["rfid_port_in"], cfg["rfid_port_out"])

    def handle_test_connection():
        import requests
        url = f"{config.get_server_base_url()}{config.ACCESS_PATH}"
        try:
            resp = requests.post(url, json={"tag_code": "__test__"},
                                 timeout=config.SERVER_TIMEOUT)
            return True, f"Conectado a {url} (HTTP {resp.status_code})"
        except Exception as exc:
            return False, f"Falha ao conectar em {url}: {exc}"

    port_in = os.getenv("RFID_PORT_IN", config.RFID_PORT_IN)
    port_out = os.getenv("RFID_PORT_OUT", config.RFID_PORT_OUT)

    shutdown_event = threading.Event()

    def _handle_sigterm(signum, frame):
        logger.info("SIGTERM recebido; encerrando...")
        shutdown_event.set()

    signal.signal(signal.SIGTERM, _handle_sigterm)

    if not headless:
        from views.main_window import MainWindow
        app = MainWindow(
            on_save_config=handle_save_config,
            on_mock_tag=handle_tag,
            on_test_connection=handle_test_connection,
            initial_config={
                "server_host": os.getenv("SERVER_HOST", config.SERVER_HOST),
                "server_port": os.getenv("SERVER_PORT", config.SERVER_PORT),
                "rfid_port_in": port_in,
                "rfid_port_out": port_out,
            },
        )

    start_readers(port_in, port_out)

    try:
        if headless:
            logger.info("Rodando em modo HEADLESS. Pressione Ctrl+C para encerrar.")
            shutdown_event.wait()
        else:
            app.mainloop()
    except KeyboardInterrupt:
        logger.info("Sinal recebido.")
    finally:
        logger.info("Encerrando serviços...")
        if reader_in:
            reader_in.stop()
        if reader_out:
            reader_out.stop()
        gate.cleanup()
        logger.info("Desligamento completo.")


if __name__ == "__main__":
    main()
