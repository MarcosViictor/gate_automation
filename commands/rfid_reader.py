from __future__ import annotations
import logging
import threading
import time
from typing import Any, Callable

import config

logger = logging.getLogger(__name__)


class RFIDReader:
    """
    Lê tags RFID em diferentes modos de conexão.

    Em modo MOCK (MOCK_HARDWARE=True) não exige hardware real -
    útil para desenvolvimento em PC.

    Em produção, suporta:
      - serial: leitura por pyserial (USB/UART)
      - hid: leitura por pacote de bytes (hidapi)
      - auto: tenta HID primeiro, depois serial

    Uso:
        reader = RFIDReader(on_tag=my_callback)
        reader.start()
        # ...
        reader.stop()
    """

    def __init__(self, on_tag: Callable[[str], None]):
        self._on_tag = on_tag
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_tag: str | None = None
        self._last_tag_time = 0.0

    def start(self):
        self._stop_event.clear()
        if config.MOCK_HARDWARE:
            logger.info("RFIDReader iniciado em modo MOCK")
            # Em mock nao levanta thread - a view injeta tags manualmente via simulate()
            return

        if self._thread and self._thread.is_alive():
            logger.debug("RFIDReader ja esta em execucao")
            return

        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()
        logger.info("RFIDReader iniciado em modo %s", config.RFID_MODE)

    def stop(self):
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
        self._thread = None

    def simulate(self, tag_code: str):
        """Injeta uma tag manualmente (apenas para mock/testes)."""
        if config.MOCK_HARDWARE:
            self._on_tag(tag_code)

    # ------------------------------------------------------------------
    # Loop principal
    # ------------------------------------------------------------------
    def _read_loop(self):
        mode = config.RFID_MODE.lower()
        if mode not in {"serial", "hid", "auto"}:
            logger.warning("RFID_MODE invalido (%s). Usando serial.", mode)
            mode = "serial"

        if mode == "auto":
            if self._can_use_hid():
                mode = "hid"
                logger.info("Modo auto: leitor HID detectado")
            else:
                mode = "serial"
                logger.info("Modo auto: HID indisponivel, usando serial")

        if mode == "hid":
            self._read_loop_hid()
        else:
            self._read_loop_serial()

    # ------------------------------------------------------------------
    # Loop serial
    # ------------------------------------------------------------------
    def _read_loop_serial(self):
        try:
            import serial  # pyserial - disponivel no Raspberry Pi
        except ImportError:
            logger.error("pyserial nao instalado. Execute: pip install pyserial")
            return

        while not self._stop_event.is_set():
            try:
                ser = serial.Serial(
                    port=config.RFID_PORT,
                    baudrate=config.RFID_BAUDRATE,
                    timeout=1,
                )
                logger.info("Leitor serial conectado em %s", config.RFID_PORT)
            except serial.SerialException as exc:
                logger.warning("Erro ao abrir porta serial: %s", exc)
                self._stop_event.wait(1)
                continue

            with ser:
                while not self._stop_event.is_set():
                    try:
                        line = ser.readline().decode("utf-8", errors="ignore").strip()
                        if line:
                            tag_code = self._parse_serial(line)
                            if tag_code:
                                logger.debug("Tag lida (serial): %s", tag_code)
                                self._emit_tag(tag_code)
                    except serial.SerialException as exc:
                        logger.warning("Leitor serial desconectado: %s", exc)
                        break
                    except Exception as exc:
                        logger.warning("Erro na leitura serial: %s", exc)

    def _parse_serial(self, raw: str) -> str | None:
        """
        Limpa a string recebida do leitor serial.
        Muitos leitores enviam STX + codigo + ETX ou apenas o codigo.
        """
        cleaned = raw.strip("\x02\x03\r\n ")  # remove STX, ETX, CRLF
        return cleaned if cleaned else None

    # ------------------------------------------------------------------
    # Loop HID
    # ------------------------------------------------------------------
    def _read_loop_hid(self):
        try:
            import hid  # type: ignore
        except ImportError:
            logger.error("hidapi nao instalado. Execute: pip install hidapi")
            return

        device = None
        while not self._stop_event.is_set():
            if device is None:
                device = self._connect_hid_device(hid)
                if device is None:
                    self._stop_event.wait(1)
                    continue

            try:
                packet_size = max(config.RFID_HID_PACKET_SIZE, 1)
                data = device.read(packet_size)

                if not data:
                    self._stop_event.wait(max(config.RFID_POLL_INTERVAL, 0.01))
                    continue

                tag_code = self._parse_hid_data(data)
                if tag_code:
                    logger.debug("Tag lida (hid): %s", tag_code)
                    self._emit_tag(tag_code)

            except (OSError, IOError) as exc:
                logger.warning("Dispositivo HID desconectado ou com erro de leitura: %s", exc)
                self._close_hid_device(device)
                device = None
                self._stop_event.wait(1)
            except Exception as exc:
                logger.warning("Erro na leitura HID: %s", exc)
                self._stop_event.wait(0.2)

        self._close_hid_device(device)

    def _can_use_hid(self) -> bool:
        try:
            import hid  # type: ignore
        except ImportError:
            return False
        return self._find_hid_device_info(hid) is not None

    def _connect_hid_device(self, hid_module: Any):
        info = self._find_hid_device_info(hid_module)
        if info is None:
            vid, pid = self._get_hid_filters()
            if vid is not None or pid is not None:
                logger.warning(
                    "Leitor HID nao encontrado para VID=%s PID=%s",
                    self._fmt_hex(vid),
                    self._fmt_hex(pid),
                )
            else:
                logger.warning("Nenhum leitor HID disponivel")
            return None

        try:
            device = hid_module.device()
            path = info.get("path")
            if path:
                device.open_path(path)
            else:
                device.open(info["vendor_id"], info["product_id"])
            device.set_nonblocking(True)

            logger.info(
                "Leitor HID conectado (VID=%s PID=%s)",
                self._fmt_hex(info.get("vendor_id")),
                self._fmt_hex(info.get("product_id")),
            )
            return device
        except Exception as exc:
            logger.error("Falha ao conectar no leitor HID: %s", exc)
            return None

    def _find_hid_device_info(self, hid_module: Any) -> dict[str, Any] | None:
        devices = hid_module.enumerate()
        if not devices:
            return None

        vid_filter, pid_filter = self._get_hid_filters()

        for dev in devices:
            vid = dev.get("vendor_id")
            pid = dev.get("product_id")
            if vid_filter is not None and vid != vid_filter:
                continue
            if pid_filter is not None and pid != pid_filter:
                continue
            return dev

        return None

    def _get_hid_filters(self) -> tuple[int | None, int | None]:
        return (
            self._parse_optional_int(config.RFID_HID_VENDOR_ID),
            self._parse_optional_int(config.RFID_HID_PRODUCT_ID),
        )

    def _parse_optional_int(self, value: str) -> int | None:
        value = (value or "").strip()
        if not value:
            return None
        try:
            return int(value, 0)  # aceita decimal e hexadecimal (ex.: 0x1234)
        except ValueError:
            logger.warning("Valor invalido para VID/PID HID: %s", value)
            return None

    @staticmethod
    def _fmt_hex(value: int | None) -> str:
        return f"0x{value:04X}" if value is not None else "*"

    def _parse_hid_data(self, data: list[int]) -> str | None:
        # Converte bytes para lista HEX (igual a logica do script base)
        hex_list = [f"{b:02X}" for b in data]

        # Remove zeros no final (padding)
        while hex_list and hex_list[-1] == "00":
            hex_list.pop()

        if not hex_list:
            return None

        # Ajuste de offset Linux/Windows (configuravel via env)
        if len(hex_list) > 20:
            offset = max(config.RFID_HID_OFFSET, 0)
            id_real = hex_list[offset:]
        else:
            id_real = hex_list

        if not id_real:
            return None

        # TAG sem espacos
        id_string = "".join(id_real)

        # Remove digitos finais (checksum/sufixo), se configurado
        strip_digits = max(config.RFID_HID_STRIP_HEX_DIGITS, 0)
        if strip_digits > 0 and len(id_string) > strip_digits:
            id_string = id_string[:-strip_digits]

        logger.debug("Recebido bruto (hid): %s", hex_list)
        logger.debug("Processado (hid): %s", id_string)
        return id_string or None

    # ------------------------------------------------------------------
    # Emissao de tag
    # ------------------------------------------------------------------
    def _emit_tag(self, tag_code: str):
        dedup_seconds = max(config.RFID_DEDUP_SECONDS, 0.0)
        now = time.monotonic()

        if (
            dedup_seconds > 0
            and self._last_tag == tag_code
            and (now - self._last_tag_time) < dedup_seconds
        ):
            logger.debug("Tag duplicada ignorada: %s", tag_code)
            return

        self._last_tag = tag_code
        self._last_tag_time = now
        self._on_tag(tag_code)

    @staticmethod
    def _close_hid_device(device: Any | None):
        if device is None:
            return
        try:
            device.close()
        except Exception:
            pass
