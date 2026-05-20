#!/bin/bash
# Script de Instalação para o Raspberry Pi

# Se a pasta estiver sob ownership do root (ex.: clonada com sudo), corrige para o usuário atual
if [ -d "/opt/gate_automation" ]; then
    echo "=== 0. Corrigindo permissões da pasta do projeto ==="
    sudo chown -R $USER:$USER /opt/gate_automation
fi

echo "=== 1. Atualizando pacotes do sistema ==="
# --allow-releaseinfo-change resolve problemas em repositórios antigos (como Raspbian Buster)
sudo apt-get update --allow-releaseinfo-change || sudo apt-get update
sudo apt-get install -y python3-tk python3-venv python3-dev gcc libusb-1.0-0-dev libhidapi-hidraw0 libhidapi-libusb0 pkg-config libhidapi-dev

echo "=== 2. Criando o ambiente virtual Python ==="
# Limpa venv anterior corrompido se existir
if [ -d "venv" ]; then
    rm -rf venv
fi
python3 -m venv venv
source venv/bin/activate

echo "=== 3. Atualizando o pip dentro do ambiente virtual ==="
pip install --upgrade pip

echo "=== 4. Instalando bibliotecas do projeto ==="
pip install -r requirements.txt
pip install hidapi

echo "=== 5. Instalando dependência do GPIO (exclusivo para Raspberry Pi) ==="
pip install RPi.GPIO

echo "=== 6. Configurando banco de dados local ==="
mkdir -p data
sudo chown -R $USER:$USER data
chmod -R 775 data

echo ""
echo "=== Instalação Concluída com Sucesso! ==="
echo "Para iniciar o sistema manualmente, execute:"
echo "./main.sh"
