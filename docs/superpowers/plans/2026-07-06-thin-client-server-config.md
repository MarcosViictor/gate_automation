# Thin Client + Configuração do Servidor — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Trocar a validação de tags do banco SQLite local por uma requisição HTTP em tempo real ao sb-gatehouse, com configuração de IP/porta do servidor persistida no `.env` e editável por uma GUI mínima.

**Architecture:** O Raspberry Pi vira thin client: lê a tag → `POST /api/raspberry/access` no servidor local → obedece o campo `open` acionando o relé (ativação inalterada). Nenhum estado local. Config (IP, porta, portas RFID) mora no `.env`; a GUI é uma camada visual sobre ele, e no Raspberry headless edita-se o `.env` direto.

**Tech Stack:** Python 3.12, `requests`, `python-dotenv`, Tkinter, `pytest` (testes em estilo `unittest`/funções). Ambiente virtual em `venv/` (usar `venv/bin/python` e `venv/bin/pytest`).

## Global Constraints

- Rodar tudo pelo venv: `venv/bin/python`, `venv/bin/pytest`.
- Fail-closed: qualquer falha de rede/servidor → acesso **negado**.
- Contrato do servidor (fixo): `POST {base}/api/raspberry/access`, body `{"tag_code": "<código>"}`, resposta 200 `{"decision","open","reason"}`. Rota pública (sem token).
- Não alterar `commands/gate_controller.py`, `commands/rfid_reader.py`, `commands/ultrasonic_sensor.py` nem a chamada `gate.open()` no acionamento.
- Mensagens de log e textos de UI em português.
- Commits frequentes, um por tarefa concluída.

---

### Task 1: Configuração do servidor no `config.py`

**Files:**
- Modify: `config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `config.SERVER_HOST: str`, `config.SERVER_PORT: str`, `config.SERVER_TIMEOUT: int`, `config.ACCESS_PATH: str = "/api/raspberry/access"`, `config.get_server_base_url() -> str`.
- Consumes: `config.update_env(key, value)` (já existe).

- [ ] **Step 1: Escrever os testes que falham**

Adicionar ao fim de `tests/test_config.py`:

```python
def test_access_path_is_fixed():
    import config
    assert config.ACCESS_PATH == "/api/raspberry/access"


def test_get_server_base_url_defaults(monkeypatch):
    monkeypatch.delenv("SERVER_HOST", raising=False)
    monkeypatch.delenv("SERVER_PORT", raising=False)
    import config
    assert config.get_server_base_url() == "http://localhost:8001"


def test_get_server_base_url_reads_env_fresh(monkeypatch):
    monkeypatch.setenv("SERVER_HOST", "192.168.0.10")
    monkeypatch.setenv("SERVER_PORT", "9000")
    import config
    assert config.get_server_base_url() == "http://192.168.0.10:9000"
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `venv/bin/pytest tests/test_config.py -v`
Expected: FAIL (`AttributeError: module 'config' has no attribute 'ACCESS_PATH'` / `get_server_base_url`).

- [ ] **Step 3: Implementar no `config.py`**

Substituir o bloco de "Servidor local (sincronização)" (as linhas de `SERVER_BASE_URL`, `SERVER_TIMEOUT`, `SYNC_INTERVAL`) por:

```python
# ==============================================================================
# Servidor local (sb-gatehouse)
# ==============================================================================
SERVER_HOST = os.getenv("SERVER_HOST", "localhost")
SERVER_PORT = os.getenv("SERVER_PORT", "8001")
SERVER_TIMEOUT = int(os.getenv("SERVER_TIMEOUT", "5"))  # segundos
ACCESS_PATH = "/api/raspberry/access"  # rota fixa do endpoint de validação


def get_server_base_url() -> str:
    """Monta a base URL lendo host/porta do ambiente a cada chamada,
    para que mudanças salvas pela GUI valham sem reiniciar."""
    host = os.getenv("SERVER_HOST", SERVER_HOST)
    port = os.getenv("SERVER_PORT", SERVER_PORT)
    return f"http://{host}:{port}"
```

Nesta tarefa **não** remover `DB_PATH` nem `SEED_TEST_DATA` (removidos na Task 4, junto com os testes que dependem deles).

- [ ] **Step 4: Rodar e ver passar**

Run: `venv/bin/pytest tests/test_config.py -v`
Expected: PASS (incluindo o `test_config_writes_to_env` existente).

- [ ] **Step 5: Commit**

```bash
git add config.py tests/test_config.py
git commit -m "feat: config de servidor (host/porta) e get_server_base_url

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: `AuthController.check` — validação HTTP com fail-closed

**Files:**
- Rewrite: `controllers/auth_controller.py`
- Test: `tests/test_auth_controller.py` (novo)

**Interfaces:**
- Consumes: `config.get_server_base_url()`, `config.ACCESS_PATH`, `config.SERVER_TIMEOUT`.
- Produces:
  - `AccessDecision(authorized: bool, tag_code: str, direction: str = "IN", reason: str | None = None, online: bool = False)` (dataclass).
  - `AuthController().check(tag_code: str, direction: str = "IN") -> AccessDecision`.

- [ ] **Step 1: Escrever os testes que falham**

Criar `tests/test_auth_controller.py`:

```python
from unittest.mock import patch, MagicMock

from controllers.auth_controller import AuthController, AccessDecision


def _fake_response(status_code, json_data=None, raise_json=False):
    resp = MagicMock()
    resp.status_code = status_code
    if raise_json:
        resp.json.side_effect = ValueError("no json")
    else:
        resp.json.return_value = json_data or {}
    return resp


def test_allowed_when_open_true():
    resp = _fake_response(200, {"decision": "allowed", "open": True})
    with patch("controllers.auth_controller.requests.post", return_value=resp):
        result = AuthController().check("TAG123", "IN")
    assert result.authorized is True
    assert result.online is True
    assert result.tag_code == "TAG123"
    assert result.direction == "IN"


def test_denied_preserves_reason():
    resp = _fake_response(200, {"decision": "denied", "open": False, "reason": "Tag inativa"})
    with patch("controllers.auth_controller.requests.post", return_value=resp):
        result = AuthController().check("TAG123")
    assert result.authorized is False
    assert result.online is True
    assert result.reason == "Tag inativa"


def test_network_error_is_fail_closed_and_offline():
    import requests
    with patch("controllers.auth_controller.requests.post",
               side_effect=requests.exceptions.ConnectionError("down")):
        result = AuthController().check("TAG123")
    assert result.authorized is False
    assert result.online is False
    assert result.reason == "Servidor inacessível"


def test_non_200_is_fail_closed_but_online():
    resp = _fake_response(500)
    with patch("controllers.auth_controller.requests.post", return_value=resp):
        result = AuthController().check("TAG123")
    assert result.authorized is False
    assert result.online is True


def test_bad_json_is_fail_closed():
    resp = _fake_response(200, raise_json=True)
    with patch("controllers.auth_controller.requests.post", return_value=resp):
        result = AuthController().check("TAG123")
    assert result.authorized is False
    assert result.online is True
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `venv/bin/pytest tests/test_auth_controller.py -v`
Expected: FAIL (o `auth_controller` atual não tem `check`/`AccessDecision`).

- [ ] **Step 3: Reescrever `controllers/auth_controller.py`**

Substituir todo o conteúdo por:

```python
from __future__ import annotations
import logging
from dataclasses import dataclass

import requests

import config

logger = logging.getLogger(__name__)


@dataclass
class AccessDecision:
    authorized: bool
    tag_code: str
    direction: str = "IN"
    reason: str | None = None
    online: bool = False


class AuthController:
    """Valida uma tag consultando o servidor local (sb-gatehouse) em tempo real.

    Fail-closed: qualquer falha de rede/servidor resulta em acesso negado.
    Para adicionar autenticação no futuro, basta incluir um header aqui
    (ex.: Authorization) lido de config/.env.
    """

    def check(self, tag_code: str, direction: str = "IN") -> AccessDecision:
        url = f"{config.get_server_base_url()}{config.ACCESS_PATH}"
        try:
            resp = requests.post(
                url, json={"tag_code": tag_code}, timeout=config.SERVER_TIMEOUT
            )
        except Exception as exc:
            logger.warning("Servidor inacessível ao checar tag %s: %s", tag_code, exc)
            return AccessDecision(False, tag_code, direction, "Servidor inacessível", online=False)

        if resp.status_code != 200:
            logger.warning("Servidor respondeu %s para a tag %s", resp.status_code, tag_code)
            return AccessDecision(
                False, tag_code, direction, f"Servidor respondeu {resp.status_code}", online=True
            )

        try:
            data = resp.json()
        except ValueError:
            logger.warning("Resposta JSON inválida do servidor para a tag %s", tag_code)
            return AccessDecision(
                False, tag_code, direction, "Resposta inválida do servidor", online=True
            )

        authorized = bool(data.get("open"))
        reason = data.get("reason") or ("Acesso liberado" if authorized else "Acesso negado")
        return AccessDecision(authorized, tag_code, direction, reason, online=True)
```

- [ ] **Step 4: Rodar e ver passar**

Run: `venv/bin/pytest tests/test_auth_controller.py -v`
Expected: PASS (5 testes).

- [ ] **Step 5: Commit**

```bash
git add controllers/auth_controller.py tests/test_auth_controller.py
git commit -m "feat: AuthController.check valida tag via HTTP (fail-closed)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: GUI mínima de status (`views/main_window.py`)

**Files:**
- Rewrite: `views/main_window.py`
- Test: `tests/test_main_window.py` (novo)

**Interfaces:**
- Consumes: `controllers.auth_controller.AccessDecision`.
- Produces:
  - `MainWindow(on_save_config, on_mock_tag, on_test_connection, initial_config)` onde:
    - `on_save_config(cfg: dict)` — `cfg` tem chaves `server_host, server_port, rfid_port_in, rfid_port_out` (strings).
    - `on_mock_tag(tag_code: str, direction: str)`.
    - `on_test_connection() -> tuple[bool, str]`.
    - `initial_config: dict` com as mesmas 4 chaves.
  - Métodos: `add_read_row(decision: AccessDecision)`, `update_gate_status(is_open: bool)`, `update_net_status(is_online: bool)`.
  - Static: `MainWindow.format_status(decision: AccessDecision) -> str`.

- [ ] **Step 1: Escrever o teste que falha**

Criar `tests/test_main_window.py`:

```python
from controllers.auth_controller import AccessDecision
from views.main_window import MainWindow


def test_format_status_authorized():
    d = AccessDecision(True, "TAG1", "IN", "Acesso liberado", online=True)
    assert MainWindow.format_status(d) == "AUTORIZADO"


def test_format_status_denied_with_reason():
    d = AccessDecision(False, "TAG1", "IN", "Tag inativa", online=True)
    assert MainWindow.format_status(d) == "NEGADO (Tag inativa)"


def test_format_status_denied_without_reason():
    d = AccessDecision(False, "TAG1", "IN", None, online=False)
    assert MainWindow.format_status(d) == "NEGADO"
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `venv/bin/pytest tests/test_main_window.py -v`
Expected: FAIL (`ImportError`/`AttributeError` — o `MainWindow` atual importa `models` e não tem `format_status`).

- [ ] **Step 3: Reescrever `views/main_window.py`**

Substituir todo o conteúdo por:

```python
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from typing import Callable

from controllers.auth_controller import AccessDecision


class MainWindow(tk.Tk):
    def __init__(
        self,
        on_save_config: Callable[[dict], None],
        on_mock_tag: Callable[[str, str], None],
        on_test_connection: Callable[[], tuple],
        initial_config: dict,
    ):
        super().__init__()
        self.on_save_config = on_save_config
        self.on_mock_tag = on_mock_tag
        self.on_test_connection = on_test_connection
        self.cfg = initial_config

        self.title("Gate Automation — Thin Client")
        self.geometry("640x460")

        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure("Success.TLabel", font=("Segoe UI", 13, "bold"), foreground="#10b981")
        style.configure("Danger.TLabel", font=("Segoe UI", 13, "bold"), foreground="#ef4444")
        style.configure("Status.TLabel", font=("Segoe UI", 13, "bold"), foreground="#1e3a8a")

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(expand=True, fill="both", padx=12, pady=12)
        self._build_monitor_tab()
        self._build_config_tab()

        self.protocol("WM_DELETE_WINDOW", self.destroy)

    # ------------------------------------------------------------------ Monitor
    def _build_monitor_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Monitor")

        top = ttk.Frame(tab)
        top.pack(fill="x", padx=10, pady=10)
        self.lbl_gate = ttk.Label(top, text="PORTÃO FECHADO", style="Status.TLabel")
        self.lbl_gate.pack(side="left")
        ttk.Label(top, text="  |  ", style="Status.TLabel").pack(side="left")
        self.lbl_net = ttk.Label(top, text="● OFFLINE", style="Danger.TLabel")
        self.lbl_net.pack(side="left")

        cols = ("time", "tag", "dir", "status")
        self.tree = ttk.Treeview(tab, columns=cols, show="headings", height=10)
        for c, t, w in (("time", "Horário", 110), ("tag", "Tag", 240),
                        ("dir", "Direção", 70), ("status", "Resultado", 180)):
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w, anchor="center" if c == "dir" else "w")
        self.tree.pack(expand=True, fill="both", padx=10, pady=(0, 10))

        sim = ttk.Frame(tab)
        sim.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Label(sim, text="Simular (ex: IN:0100... ou só o código):").pack(side="left", padx=(0, 8))
        self.ent_mock = ttk.Entry(sim, font=("Consolas", 10))
        self.ent_mock.pack(side="left", fill="x", expand=True, padx=5)
        self.ent_mock.bind("<Return>", lambda e: self._handle_mock())
        ttk.Button(sim, text="Ler Tag", command=self._handle_mock).pack(side="right", padx=5)

    def _handle_mock(self):
        val = self.ent_mock.get().strip()
        if not val:
            return
        if val.startswith("IN:"):
            self.on_mock_tag(val[3:], "IN")
        elif val.startswith("OUT:"):
            self.on_mock_tag(val[4:], "OUT")
        else:
            self.on_mock_tag(val, "IN")
        self.ent_mock.delete(0, tk.END)

    # ------------------------------------------------------------------ Config
    def _build_config_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Configurações")

        frame = ttk.Frame(tab)
        frame.pack(fill="both", padx=25, pady=25)

        ttk.Label(frame, text="Servidor local (sb-gatehouse)",
                  font=("Segoe UI", 13, "bold"), foreground="#1e3a8a").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))

        self.ent_host = self._labeled_entry(frame, "IP do servidor:", 1, self.cfg["server_host"])
        self.ent_port = self._labeled_entry(frame, "Porta:", 2, self.cfg["server_port"])
        self.ent_in = self._labeled_entry(frame, "Leitor Entrada (IN):", 3, self.cfg["rfid_port_in"])
        self.ent_out = self._labeled_entry(frame, "Leitor Saída (OUT):", 4, self.cfg["rfid_port_out"])

        btns = ttk.Frame(frame)
        btns.grid(row=5, column=1, sticky="e", pady=(18, 0))
        ttk.Button(btns, text="Testar conexão", command=self._test_connection).pack(side="left", padx=6)
        ttk.Button(btns, text="✓ Salvar", command=self._save_config).pack(side="left")

    def _labeled_entry(self, parent, label, row, value):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=8)
        ent = ttk.Entry(parent, width=32, font=("Consolas", 10))
        ent.insert(0, value or "")
        ent.grid(row=row, column=1, padx=12, pady=8)
        return ent

    def _collect_config(self) -> dict:
        return {
            "server_host": self.ent_host.get().strip(),
            "server_port": self.ent_port.get().strip(),
            "rfid_port_in": self.ent_in.get().strip(),
            "rfid_port_out": self.ent_out.get().strip(),
        }

    def _save_config(self):
        self.cfg = self._collect_config()
        self.on_save_config(self.cfg)
        messagebox.showinfo("Configurações", "Salvo no .env e leitores reiniciados.")

    def _test_connection(self):
        # Salva antes de testar, para usar o IP/porta digitados.
        self.on_save_config(self._collect_config())
        ok, msg = self.on_test_connection()
        if ok:
            messagebox.showinfo("Testar conexão", msg)
        else:
            messagebox.showerror("Testar conexão", msg)

    # ------------------------------------------------------------------ Updates
    @staticmethod
    def format_status(decision: AccessDecision) -> str:
        if decision.authorized:
            return "AUTORIZADO"
        return f"NEGADO ({decision.reason})" if decision.reason else "NEGADO"

    def add_read_row(self, decision: AccessDecision):
        self.tree.insert(
            "", 0,
            values=(datetime.now().strftime("%H:%M:%S"), decision.tag_code,
                    decision.direction, self.format_status(decision)),
        )
        children = self.tree.get_children()
        for extra in children[15:]:
            self.tree.delete(extra)

    def update_gate_status(self, is_open: bool):
        self.lbl_gate.config(
            text="PORTÃO ABERTO" if is_open else "PORTÃO FECHADO",
            style="Success.TLabel" if is_open else "Status.TLabel",
        )

    def update_net_status(self, is_online: bool):
        self.lbl_net.config(
            text="● ONLINE" if is_online else "● OFFLINE",
            style="Success.TLabel" if is_online else "Danger.TLabel",
        )
```

- [ ] **Step 4: Rodar e ver passar**

Run: `venv/bin/pytest tests/test_main_window.py -v`
Expected: PASS (3 testes).

- [ ] **Step 5: Commit**

```bash
git add views/main_window.py tests/test_main_window.py
git commit -m "feat: GUI mínima de status (monitor + configuracoes)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Remover banco local, sync e artefatos; limpar config; `.gitignore` e `.env.example`

**Files:**
- Delete: `models/` (diretório inteiro), `controllers/sync_controller.py`, `data/gate_local.db`
- Delete: `tests/test_database.py`, `tests/test_vehicle.py`, `tests/test_access_log.py`
- Modify: `config.py` (remover `DB_PATH`, `SEED_TEST_DATA`)
- Rewrite: `.gitignore`
- Create: `.env.example`

**Interfaces:**
- Produces: repositório sem dependências do banco; `.env.example` documentando as chaves.

- [ ] **Step 1: Apagar código e artefatos do banco**

```bash
git rm -r models/
git rm controllers/sync_controller.py
git rm tests/test_database.py tests/test_vehicle.py tests/test_access_log.py
git rm --cached data/gate_local.db
rm -f data/gate_local.db
```

- [ ] **Step 2: Limpar `config.py`**

Remover o bloco de "Caminhos" que define `DB_PATH`:

```python
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "gate_local.db")
```
(manter apenas o `BASE_DIR` já definido no topo do arquivo, junto do `ENV_FILE_PATH`).

E remover a atribuição de `SEED_TEST_DATA`:

```python
SEED_TEST_DATA = os.getenv(
	"SEED_TEST_DATA",
	"true" if MOCK_HARDWARE else "false",
).lower() == "true"
```

- [ ] **Step 3: Reescrever `.gitignore`**

Substituir todo o conteúdo por:

```gitignore
# Python
__pycache__/
*.py[cod]
venv/
.venv/

# Ambiente / dados locais
.env
data/*.db
```

- [ ] **Step 4: Criar `.env.example`**

```dotenv
# Endereço do servidor local (sb-gatehouse)
SERVER_HOST=localhost
SERVER_PORT=8001

# Portas dos leitores RFID
RFID_PORT_IN=/dev/ttyUSB0
RFID_PORT_OUT=/dev/ttyUSB1

# Hardware
MOCK_HARDWARE=false
RFID_MODE=hid
```

- [ ] **Step 5: Rodar a suíte inteira e ver verde**

Run: `venv/bin/pytest -v`
Expected: PASS — restam `test_config`, `test_auth_controller`, `test_main_window`, `test_gate_controller`, `test_ultrasonic_config`, `test_ultrasonic_sensor`. Nenhum erro de import de `models`.

Se algum teste de ultrassom/gate importar `models`, ajustar o import (não deve — eles usam `commands/` e `config`). Confirmar com:
`grep -rn "import models\|from models" tests/ commands/ views/ controllers/`
Expected: sem resultados. (O `main.py` ainda importa `models` neste ponto — ele é reescrito na Task 5; por isso não entra neste grep e não é coletado pelo pytest.)

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "refactor: remove banco local, sync e seed; .gitignore Python + .env.example

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: Reescrever `main.py` (thin client)

**Files:**
- Rewrite: `main.py`

**Interfaces:**
- Consumes: `AuthController.check`, `AccessDecision`, `RFIDReader`, `GateController`, `config.get_server_base_url`, `config.ACCESS_PATH`, `config.update_env`, `MainWindow(...)`.

- [ ] **Step 1: Reescrever `main.py`**

Substituir todo o conteúdo por:

```python
"""Ponto de entrada — Gate Automation (thin client).

Lê tags RFID e valida em tempo real no servidor local (sb-gatehouse).
Config de servidor/portas vem do .env (editável pela GUI ou por SSH no Raspberry).

Variáveis de ambiente:
    HEADLESS=true        Força modo sem GUI (auto-detectado se não houver DISPLAY)
    MOCK_HARDWARE=true   Roda sem GPIO/serial (a GUI injeta tags manualmente)
"""
import os
import sys
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
            threading.Event().wait()
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
```

- [ ] **Step 2: Smoke test — boot headless mock**

```bash
MOCK_HARDWARE=true HEADLESS=true venv/bin/python main.py > /tmp/gate_boot.log 2>&1 &
sleep 2 && kill %1
grep -q "modo HEADLESS" /tmp/gate_boot.log && echo "BOOT OK" || (cat /tmp/gate_boot.log; echo "BOOT FALHOU")
```
Expected: `BOOT OK`, sem tracebacks no log.

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "feat: main.py thin client (auth via HTTP, config .env, sem banco)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: Verificação end-to-end contra servidor stub

**Files:**
- Test: `tests/test_integration_access.py` (novo)

**Interfaces:**
- Consumes: `AuthController.check` contra um servidor HTTP real (stub) que imita o contrato do sb-gatehouse.

- [ ] **Step 1: Escrever o teste de integração**

Criar `tests/test_integration_access.py`:

```python
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from controllers.auth_controller import AuthController


class _StubHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        # Regra do stub: tag "OK" libera; qualquer outra nega.
        allowed = body.get("tag_code") == "OK"
        payload = {
            "decision": "allowed" if allowed else "denied",
            "open": allowed,
        }
        if not allowed:
            payload["reason"] = "Tag inativa"
        data = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass  # silencia o log do servidor


@pytest.fixture
def stub_server(monkeypatch):
    server = HTTPServer(("127.0.0.1", 0), _StubHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setenv("SERVER_HOST", "127.0.0.1")
    monkeypatch.setenv("SERVER_PORT", str(port))
    yield port
    server.shutdown()


def test_allowed_against_real_server(stub_server):
    result = AuthController().check("OK", "IN")
    assert result.authorized is True
    assert result.online is True


def test_denied_against_real_server(stub_server):
    result = AuthController().check("NOPE", "IN")
    assert result.authorized is False
    assert result.online is True
    assert result.reason == "Tag inativa"


def test_offline_when_server_down(monkeypatch):
    # Porta sem ninguém escutando -> fail-closed offline.
    monkeypatch.setenv("SERVER_HOST", "127.0.0.1")
    monkeypatch.setenv("SERVER_PORT", "9")  # porta reservada, recusa conexão
    result = AuthController().check("OK", "IN")
    assert result.authorized is False
    assert result.online is False
```

- [ ] **Step 2: Rodar o teste de integração**

Run: `venv/bin/pytest tests/test_integration_access.py -v`
Expected: PASS (3 testes).

- [ ] **Step 3: Rodar a suíte completa**

Run: `venv/bin/pytest -v`
Expected: PASS em todos (config, auth_controller, main_window, integration_access, gate_controller, ultrasonic).

- [ ] **Step 4: Drive manual da GUI (opcional, requer tela)**

```bash
MOCK_HARDWARE=true venv/bin/python main.py
```
Na janela: aba **Configurações** → confirmar IP `localhost` / porta `8001` → **Testar conexão** (mostra ✅ se o sb-gatehouse estiver no ar, ❌ caso contrário). Aba **Monitor** → digitar um código no simulador → **Ler Tag** → linha aparece com AUTORIZADO/NEGADO e o status do portão/rede atualiza.

- [ ] **Step 5: Commit**

```bash
git add tests/test_integration_access.py
git commit -m "test: integração end-to-end de acesso contra servidor stub

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Notas de verificação final

- Toda a suíte deve passar: `venv/bin/pytest -v`.
- App sobe headless sem banco: `MOCK_HARDWARE=true HEADLESS=true venv/bin/python main.py`.
- Config de servidor persiste no `.env` tanto pela GUI quanto por edição direta (Raspberry headless).
- Ativação do relé (`gate.open()`) permanece inalterada.
