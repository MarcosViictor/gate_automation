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
