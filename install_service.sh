#!/bin/bash
# Script para instalar o serviço systemd no Raspberry Pi

echo "=== Configurando Serviço Systemd para Gate Automation ==="

# 1. Garante que a pasta /opt/gate_automation existe e tem permissão correta
sudo mkdir -p /opt/gate_automation
sudo chown -R $USER:$USER /opt/gate_automation

# 2. Copia os arquivos do projeto para /opt/gate_automation (ignorando venv e .git)
echo "=== Copiando arquivos do projeto para /opt/gate_automation ==="
if command -v rsync >/dev/null 2>&1; then
    rsync -rlptD --exclude='venv' --exclude='.git' --exclude='.agent' --exclude='__pycache__' ./ /opt/gate_automation/
else
    # Fallback caso rsync não esteja instalado
    sudo cp -R . /opt/gate_automation/
    sudo chown -R $USER:$USER /opt/gate_automation
    rm -rf /opt/gate_automation/venv
    rm -rf /opt/gate_automation/.git
    rm -rf /opt/gate_automation/.agent
fi

# 3. Entra na pasta de destino e roda o setup.sh para gerar o ambiente virtual lá
cd /opt/gate_automation
echo "=== Configurando ambiente virtual em /opt/gate_automation ==="
chmod +x setup.sh
./setup.sh

# 4. Copia o arquivo do serviço para a pasta do systemd
sudo cp gate_automation.service /etc/systemd/system/gate_automation.service

# 5. Recarrega os daemons do systemd para ler o novo arquivo
sudo systemctl daemon-reload

# 6. Habilita o serviço para iniciar no boot
sudo systemctl enable gate_automation.service

# 7. Inicia/Reinicia o serviço agora
sudo systemctl restart gate_automation.service

echo "=== Serviço Instalado e Iniciado com Sucesso! ==="
echo "Você pode verificar o status usando: sudo systemctl status gate_automation"
echo "Você pode ver os logs usando: sudo journalctl -u gate_automation -f"

