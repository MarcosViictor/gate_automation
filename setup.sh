#!/bin/bash
# Script de Instalação para o Raspberry Pi

echo "=== 1. Atualizando pacotes do sistema ==="
sudo apt-get update
sudo apt-get install -y python3-tk python3-venv python3-dev gcc libusb-1.0-0-dev libhidapi-hidraw0 libhidapi-libusb0

echo "=== 2. Criando o ambiente virtual Python ==="
python3 -m venv venv
source venv/bin/activate

echo "=== 3. Instalando bibliotecas do projeto ==="
pip install -r requirements.txt

echo "=== 4. Instalando dependência do GPIO (exclusivo para Raspberry Pi) ==="
pip install RPi.GPIO

echo "=== Instalação Concluída! ==="
echo "Para iniciar o sistema, rode os seguintes comandos:"
echo "source venv/bin/activate"
echo "python3 main.py"
