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

    def __init__(self, reader_id: str, port_name: str, on_tag: Callable[[str, str], None]):
        self.reader_id = reader_id
        self.port_name = port_name
        self._on_tag = on_tag
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_tag: str | None = None
        self._last_tag_time = 0.0
        self._hid_candidates: list[dict[str, Any]] = []
        self._hid_candidate_idx = 0

    def start(self):
        self._stop_event.clear()
        if config.MOCK_HARDWARE:
            logger.info("RFIDReader [%s] iniciado em modo MOCK", self.reader_id)
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
            self._on_tag(tag_code, self.reader_id)

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
                    port=self.port_name,
                    baudrate=config.RFID_BAUDRATE,
                    timeout=1,
                )
                logger.info("Leitor serial [%s] conectado em %s", self.reader_id, self.port_name)
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
                                logger.debug("Tag lida (serial %s): %s", self.reader_id, tag_code)
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
        device_info: dict[str, Any] | None = None
        last_data_at = 0.0

        while not self._stop_event.is_set():
            if device is None:
                device, device_info = self._connect_hid_device(hid)
                if device is None:
                    self._stop_event.wait(1)
                    continue
                last_data_at = time.monotonic()

            try:
                packet_size = max(config.RFID_HID_PACKET_SIZE, 1)
                data = device.read(packet_size)

                if not data:
                    # Alguns leitores expõem multiplas interfaces HID. Se a interface atual
                    # ficar sem dados, avanca para a proxima candidata automaticamente.
                    idle_seconds = max(config.RFID_HID_INTERFACE_IDLE_SECONDS, 0.0)
                    if (
                        idle_seconds > 0
                        and len(self._hid_candidates) > 1
                        and (time.monotonic() - last_data_at) >= idle_seconds
                    ):
                        logger.info(
                            "Interface HID sem dados por %.1fs; tentando proxima interface",
                            idle_seconds,
                        )
                        self._close_hid_device(device)
                        device = None
                        device_info = None
                        continue

                    self._stop_event.wait(max(config.RFID_POLL_INTERVAL, 0.01))
                    continue

                last_data_at = time.monotonic()

                tag_code = self._parse_hid_data(data)
                if tag_code:
                    logger.debug("Tag lida (hid %s): %s", self.reader_id, tag_code)
                    self._emit_tag(tag_code)

            except (OSError, IOError) as exc:
                logger.warning("Dispositivo HID desconectado ou com erro de leitura: %s", exc)
                self._close_hid_device(device)
                device = None
                device_info = None
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
        return bool(self._list_hid_candidates(hid))

    def _connect_hid_device(self, hid_module: Any):
        self._hid_candidates = self._list_hid_candidates(hid_module)

        if not self._hid_candidates:
            vid, pid = self._get_hid_filters()
            if vid is not None or pid is not None:
                logger.warning(
                    "Leitor HID nao encontrado para VID=%s PID=%s",
                    self._fmt_hex(vid),
                    self._fmt_hex(pid),
                )
            else:
                logger.warning("Nenhum leitor HID disponivel")
            return None, None

        info = self._hid_candidates[self._hid_candidate_idx % len(self._hid_candidates)]
        self._hid_candidate_idx = (self._hid_candidate_idx + 1) % len(self._hid_candidates)

        try:
            device = hid_module.device()
            path = info.get("path")
            if path:
                device.open_path(path)
            else:
                device.open(info["vendor_id"], info["product_id"])
            device.set_nonblocking(True)

            logger.info(
                (
                    "Leitor HID [%s] conectado (VID=%s PID=%s interface=%s usage_page=%s usage=%s)"
                ),
                self.reader_id,
                self._fmt_hex(info.get("vendor_id")),
                self._fmt_hex(info.get("product_id")),
                info.get("interface_number", "*"),
                self._fmt_hex(info.get("usage_page")),
                self._fmt_hex(info.get("usage")),
            )
            return device, info
        except Exception as exc:
            logger.error("Falha ao conectar no leitor HID: %s", exc)
            return None, None

    def _list_hid_candidates(self, hid_module: Any) -> list[dict[str, Any]]:
        devices = hid_module.enumerate()
        if not devices:
            return []

        vid_filter, pid_filter = self._get_hid_filters()
        interface_filter = self._parse_optional_int(config.RFID_HID_INTERFACE_NUMBER)
        usage_page_filter = self._parse_optional_int(config.RFID_HID_USAGE_PAGE)
        usage_filter = self._parse_optional_int(config.RFID_HID_USAGE)

        candidates: list[dict[str, Any]] = []

        for dev in devices:
            vid = dev.get("vendor_id")
            pid = dev.get("product_id")
            interface_number = dev.get("interface_number")
            usage_page = dev.get("usage_page")
            usage = dev.get("usage")

            if vid_filter is not None and vid != vid_filter:
                continue
            if pid_filter is not None and pid != pid_filter:
                continue
            if interface_filter is not None and interface_number != interface_filter:
                continue
            if usage_page_filter is not None and usage_page != usage_page_filter:
                continue
            if usage_filter is not None and usage != usage_filter:
                continue

            candidates.append(dev)

        # Priorizacao para interfaces tipicas de leitores RFID
        candidates.sort(
            key=lambda d: (
                0 if d.get("usage_page") == 0xFF00 else 1,
                0 if d.get("usage") == 1 else 1,
                d.get("interface_number") if d.get("interface_number") is not None else 999,
            )
        )

        if config.RFID_HID_LOG_ENUMERATION and candidates:
            for idx, dev in enumerate(candidates):
                logger.info(
                    (
                        "HID candidato %d: VID=%s PID=%s interface=%s usage_page=%s usage=%s"
                    ),
                    idx,
                    self._fmt_hex(dev.get("vendor_id")),
                    self._fmt_hex(dev.get("product_id")),
                    dev.get("interface_number", "*"),
                    self._fmt_hex(dev.get("usage_page")),
                    self._fmt_hex(dev.get("usage")),
                )

        return candidates

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
            logger.warning("Valor inteiro invalido em configuracao HID: %s", value)
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

        strip_digits = max(config.RFID_HID_STRIP_HEX_DIGITS, 0)

        # Tenta offset principal e fallback 17/18/19 automaticamente.
        base_offset = max(config.RFID_HID_OFFSET, 0)
        offset_candidates = [base_offset]
        for fallback in (17, 18, 19):
            if fallback not in offset_candidates:
                offset_candidates.append(fallback)

        for offset in offset_candidates:
            if len(hex_list) > 20:
                id_real = hex_list[offset:]
            else:
                id_real = hex_list

            if not id_real:
                continue

            id_string = "".join(id_real)
            if strip_digits > 0 and len(id_string) > strip_digits:
                id_string = id_string[:-strip_digits]

            if id_string:
                logger.debug("Recebido bruto (hid): %s", hex_list)
                logger.debug("Processado (hid) offset=%d: %s", offset, id_string)
                return id_string

        return None

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
        self._on_tag(tag_code, self.reader_id)

    @staticmethod
    def _close_hid_device(device: Any | None):
        if device is None:
            return
        try:
            device.close()
        except Exception:
            pass
