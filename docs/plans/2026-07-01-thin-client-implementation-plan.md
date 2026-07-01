# Thin Client Architecture Implementation Plan

> **For Antigravity:** REQUIRED WORKFLOW: Use `.agent/workflows/execute-plan.md` to execute this plan in single-flow mode.

**Goal:** Refactor the system into a Thin Client architecture by removing the local SQLite database and adding dynamic `.env` configuration via the UI.

**Architecture:** The Raspberry Pi will remove all local data sync logic, making real-time HTTP requests to the Fog server for tag validation. Configurations (IP, RFID ports) will be stored in a `.env` file and editable via the UI.

**Tech Stack:** Python, `python-dotenv`, `requests`, Tkinter.

---

### Task 1: Add Configuration Management (`.env`)

**Files:**
- Modify: `requirements.txt`
- Modify: `config.py`
- Modify: `setup.sh`

**Step 1: Write the failing test**

```python
def test_config_writes_to_env(tmp_path):
    from unittest.mock import patch
    import config
    
    env_file = tmp_path / ".env"
    with patch("config.ENV_FILE_PATH", str(env_file)):
        config.update_env("TEST_KEY", "123")
        
    assert "TEST_KEY=123" in env_file.read_text()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`
Expected: FAIL (module not found / missing function)

**Step 3: Write minimal implementation**

Modify `requirements.txt`:
```text
python-dotenv>=1.0.0
```

Modify `config.py`:
```python
import os
from dotenv import load_dotenv, set_key

ENV_FILE_PATH = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(ENV_FILE_PATH)

SERVER_BASE_URL = os.getenv("SERVER_BASE_URL", "http://sitiobarreiras.app.br:55432")
# ... other existing variables

def update_env(key: str, value: str):
    if not os.path.exists(ENV_FILE_PATH):
        open(ENV_FILE_PATH, 'a').close()
    set_key(ENV_FILE_PATH, key, value)
    os.environ[key] = value
```

Modify `setup.sh` (remove local db setup lines 35-39).

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add requirements.txt config.py setup.sh tests/test_config.py
git commit -m "feat: add dotenv configuration manager"
```

---

### Task 2: Refactor UI for Network Config

**Files:**
- Modify: `views/main_window.py`
- Modify: `main.py`

**Step 1: Write the failing test**
(No easy automated UI test, skip failing test, rely on manual/syntax check).

**Step 2: Write minimal implementation**

Modify `views/main_window.py`:
- In `__init__`, remove `db` dependency.
- Add fields in "Configurações" tab for `SERVER_BASE_URL`, `RFID_PORT_IN`, `RFID_PORT_OUT`.
- Pre-fill them from `config.SERVER_BASE_URL`, etc.
- In `save_ports`, call `config.update_env()` for each field, then call `on_save_ports(port_in, port_out, server_url)`.

Modify `main.py`:
- Remove `Database()` instantiation.
- Update `handle_save_ports` signature and logic to accept the new server URL.

**Step 3: Verify syntax**
Run: `python3 -m py_compile views/main_window.py main.py`
Expected: PASS (no output)

**Step 4: Commit**

```bash
git add views/main_window.py main.py
git commit -m "feat: add configuration tab for IP and ports"
```

---

### Task 3: Refactor AuthController

**Files:**
- Modify: `controllers/auth_controller.py`
- Modify: `tests/test_auth_controller.py`

**Step 1: Write the failing test**

```python
def test_auth_controller_api_call(mocker):
    from controllers.auth_controller import AuthController
    
    mock_post = mocker.patch("requests.post")
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"status": "ok"}
    
    auth = AuthController()
    result = auth.process("123", "IN")
    assert result.authorized is True
    mock_post.assert_called_once()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_auth_controller.py -v`
Expected: FAIL 

**Step 3: Write minimal implementation**

Modify `controllers/auth_controller.py`:
```python
import requests
import logging
import config
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class AuthResult:
    authorized: bool
    reason: str = ""

class AuthController:
    def __init__(self, mode="online"):
        self.mode = mode

    def process(self, tag_code: str, direction: str) -> AuthResult:
        logger.info(f"Checking tag {tag_code} ({direction}) with local server...")
        try:
            url = f"{config.SERVER_BASE_URL}/api/gate/check"
            payload = {"tag_code": tag_code, "direction": direction}
            
            # 2 second timeout to prevent freezing the gate if network drops
            resp = requests.post(url, json=payload, timeout=2.0)
            
            if resp.status_code == 200:
                return AuthResult(authorized=True, reason="Autorizado via Servidor Local")
            elif resp.status_code == 404:
                return AuthResult(authorized=False, reason="Tag não encontrada/inválida")
            else:
                return AuthResult(authorized=False, reason=f"Erro do Servidor: {resp.status_code}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro de conexão com o servidor local: {e}")
            return AuthResult(authorized=False, reason="Falha na Rede")
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_auth_controller.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add controllers/auth_controller.py tests/test_auth_controller.py
git commit -m "refactor: transition AuthController to thin client API"
```

---

### Task 4: Remove Legacy Database and Sync Logic

**Files:**
- Delete: `models/database.py`, `models/access_log.py`, `models/driver.py`, `models/schedule.py`, `models/tag.py`, `models/vehicle.py`, `models/seed.py`
- Delete: `controllers/sync_controller.py`
- Modify: `main.py`
- Modify: `tests/*`

**Step 1: Write minimal implementation**

- Delete all files mentioned above.
- In `main.py`, remove all imports and references to `SyncController`, `Database`, `Tag`, `Vehicle`, `Driver`.
- Remove `_seed_test_data` logic and `sync.start()`, `sync.stop()`.
- Delete `tests/test_database.py`, `tests/test_vehicle.py`, `tests/test_access_log.py`.

**Step 2: Verify tests and syntax**

Run: `pytest -v`
Expected: Remaining tests pass without DB dependencies.

**Step 3: Commit**

```bash
git rm models/*.py controllers/sync_controller.py tests/test_database.py tests/test_vehicle.py tests/test_access_log.py
git add main.py
git commit -m "refactor: remove local database and background sync logic"
```
