# Raspberry Pi Auto-start Implementation Plan

> **For Antigravity:** REQUIRED WORKFLOW: Use `.agent/workflows/execute-plan.md` to execute this plan in single-flow mode.

**Goal:** Configure the Gate Automation system to run automatically on Raspberry Pi boot using a systemd service running inside the virtual environment as root.

**Architecture:** Modify the existing `gate_automation.service` to point directly to the virtual environment python interpreter (`venv/bin/python`) and specify systemd environment variables. Create an `install_service.sh` shell script to automate installation and setup of the service.

**Tech Stack:** systemd, bash, python3

---

### Task 1: Configure `gate_automation.service`

**Files:**
- Modify: `/home/victor/dev/gate_automation/gate_automation.service`

**Step 1: Write the updated systemd service file**
Edit `/home/victor/dev/gate_automation/gate_automation.service` to match the following configuration:

```ini
[Unit]
Description=Serviço de Automação de Portão (Gate Automation)
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/gate_automation
ExecStart=/opt/gate_automation/venv/bin/python main.py
Environment=HEADLESS=true
Environment=MOCK_HARDWARE=false
Environment=RFID_MODE=hid
Environment=RFID_HID_VENDOR_ID=0x1A86
Environment=RFID_HID_PRODUCT_ID=0xE010
Environment=RFID_HID_OFFSET=18
Environment=RFID_HID_STRIP_HEX_DIGITS=6
EnvironmentFile=-/opt/gate_automation/.env
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**Step 2: Run verification**
Verify that the format of the service file conforms to systemd standards using `systemd-analyze verify` (mocked format check as we are not installing it yet):
Run: `grep -q "ExecStart=/opt/gate_automation/venv/bin/python main.py" gate_automation.service`
Expected: Exits with status 0.

**Step 3: Commit**
```bash
git add gate_automation.service
git commit -m "chore: configure systemd service to use virtualenv python and env vars"
```

---

### Task 2: Create `install_service.sh`

**Files:**
- Create: `/home/victor/dev/gate_automation/install_service.sh`

**Step 1: Write the installer script**
Create the file `/home/victor/dev/gate_automation/install_service.sh` with the following content:

```bash
#!/bin/bash
# Script para instalar o serviço systemd no Raspberry Pi

echo "=== Configurando Serviço Systemd para Gate Automation ==="

# 1. Copia o arquivo para a pasta do systemd
sudo cp gate_automation.service /etc/systemd/system/gate_automation.service

# 2. Recarrega os daemons do systemd para ler o novo arquivo
sudo systemctl daemon-reload

# 3. Habilita o serviço para iniciar no boot
sudo systemctl enable gate_automation.service

# 4. Inicia o serviço agora
sudo systemctl start gate_automation.service

echo "=== Serviço Instalado e Iniciado com Sucesso! ==="
echo "Você pode verificar o status usando: sudo systemctl status gate_automation"
echo "Você pode ver os logs usando: sudo journalctl -u gate_automation -f"
```

**Step 2: Run verification**
Check the shell script syntax to ensure there are no syntax errors.
Run: `bash -n install_service.sh`
Expected: Exits with status 0 (no output).

Set executable permissions:
Run: `chmod +x install_service.sh`
Expected: File is executable.

**Step 3: Commit**
```bash
git add install_service.sh
git commit -m "feat: add service installation script for Raspberry Pi"
```
