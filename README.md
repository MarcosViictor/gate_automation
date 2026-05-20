# Gate Automation 🚪🔒

Sistema completo de controle de acesso de portaria automatizada, com leitura física de tags RFID (USB HID / Serial), validação de credenciais local (banco SQLite offline-first) e sincronização assíncrona com o servidor na nuvem.

A aplicação suporta execução **com interface gráfica (Tkinter)** e **modo silencioso (Headless)** para rodar em servidores ou Raspberry Pi sem tela.

---

## 🛠️ Requisitos do Sistema

* **Sistema Operacional:** Linux (Raspberry Pi OS, Debian, Ubuntu, etc.)
* **Python:** Versão 3.8 ou superior
* **Bibliotecas de Sistema:**
  * `python3-tk` (para suporte à interface Tkinter)
  * `libusb-1.0-0-dev`, `libhidapi-dev` e `pkg-config` (para comunicação USB HID com os leitores RFID)
  * `gcc` e `python3-dev` (para compilar dependências do Python)

---

## 📦 Passos para Instalação

Recomendamos instalar o projeto na pasta `/opt/gate_automation`.

### 1. Clonar o Projeto para o Diretório Correto
```bash
# Clone o repositório
sudo git clone https://github.com/MarcosViictor/gate_automation.git /opt/gate_automation

# CORREÇÃO CRÍTICA DE PERMISSÃO: Altere a propriedade para o seu usuário (ex: pi)
sudo chown -R $USER:$USER /opt/gate_automation
cd /opt/gate_automation
```

### 2. Executar o Script de Instalação
O projeto inclui o script `setup.sh` que automatiza a atualização de repositórios, instalação das dependências do sistema Linux, criação do ambiente virtual Python (`venv`), atualização do `pip` (evita falhas de sintaxe na compilação do `hidapi`) e instalação dos pacotes necessários:
```bash
chmod +x setup.sh
./setup.sh
```

---

## 🚀 Como Executar

O projeto possui um wrapper unificado chamado [main.sh](file:///opt/gate_automation/main.sh) que configura o ambiente virtual e variáveis padrão de hardware de forma automática.

### Cenário A: Com Tela (Interface Gráfica)
Se você estiver em um ambiente de desktop Linux normal, basta executar:
```bash
./main.sh
```

### Cenário B: Sem Tela (Modo Headless / Daemon)
Se você estiver rodando em um Raspberry Pi sem monitor (via SSH, por exemplo), o sistema detectará automaticamente a ausência do display e iniciará em **modo Headless** (silencioso).

Você também pode forçar a execução Headless explicitamente:
```bash
HEADLESS=true ./main.sh
```

---

## 🔄 Inicialização Automática no Boot (Serviço Systemd)

Para fazer o sistema rodar automaticamente sempre que o computador/Raspberry Pi for ligado (em modo Headless, sem necessidade de monitor ou login do usuário), configure o serviço do `systemd`:

1. **Copie o arquivo de serviço para a pasta do sistema:**
   ```bash
   sudo cp /opt/gate_automation/gate_automation.service /etc/systemd/system/
   ```

2. **Recarregue as configurações do systemd:**
   ```bash
   sudo systemctl daemon-reload
   ```

3. **Habilite a inicialização automática no boot:**
   ```bash
   sudo systemctl enable gate_automation.service
   ```

4. **Inicie o serviço imediatamente:**
   ```bash
   sudo systemctl start gate_automation.service
   ```

5. **Verifique se o serviço está funcionando corretamente:**
   ```bash
   sudo systemctl status gate_automation.service
   ```

Para monitorar os logs em tempo real do serviço em segundo plano:
```bash
sudo journalctl -u gate_automation.service -f
```

---

## ⚙️ Configuração de Leitores RFID

As portas físicas do leitor de Entrada (`IN`) e Saída (`OUT`) são recuperadas do banco de dados local. Você pode configurar as variáveis de hardware padrão no arquivo [config.py](file:///opt/gate_automation/config.py) ou no script [main.sh](file:///opt/gate_automation/main.sh).

---

## 🛠️ Resolução de Problemas Comuns (Troubleshooting)

### 1. Erro: `sqlite3.OperationalError: attempt to write a readonly database`
* **Causa:** O banco de dados SQLite ou a pasta `data/` estão protegidos como somente leitura (geralmente porque foram criados ao executar a aplicação anteriormente com `sudo python3` ou o dono da pasta era o `root`).
* **Solução:** Execute o comando de ajuste de permissões:
  ```bash
  sudo chown -R $USER:$USER /opt/gate_automation/data
  chmod -R 775 /opt/gate_automation/data
  ```

### 2. Erro no `apt update`: `buster Release no longer has a Release file`
* **Causa:** O repositório Debian Buster (antigo) do Raspberry Pi chegou ao Fim de Vida (EOL) e gera alertas de segurança que impedem o `apt-get update` padrão de rodar.
* **Solução:** O script `setup.sh` contorna isso automaticamente rodando com a flag especial de release, mas caso precise rodar manualmente:
  ```bash
  sudo apt-get update --allow-releaseinfo-change
  ```

### 3. Erro: `OSError: [Errno 13] Permissão negada` ao rodar `pip install`
* **Causa:** O repositório foi clonado usando `sudo git clone`, tornando o `root` proprietário das pastas do projeto. Ao rodar `pip install` dentro do venv como usuário comum, o sistema impede a escrita.
* **Solução:** Altere a propriedade de todo o projeto para o usuário comum:
  ```bash
  sudo chown -R $USER:$USER /opt/gate_automation
  ```
  *(Nota: Nunca execute comandos `pip install` com `sudo` dentro do ambiente virtual).*

### 4. Erro ao compilar `hidapi`: `pkg-config package 'libusb-1.0' not found` ou `SyntaxError: invalid syntax`
* **Causa:** Faltam as bibliotecas nativas de desenvolvimento do USB e compiladores, ou o pip instalado no ambiente virtual está desatualizado e tenta baixar uma versão antiga do hidapi que não possui suporte a compilador moderno.
* **Solução:** Certifique-se de instalar as dependências nativas e atualizar o pip primeiro:
  ```bash
  sudo apt-get install -y libusb-1.0-0-dev libhidapi-dev pkg-config python3-dev
  source venv/bin/activate
  pip install --upgrade pip
  pip install hidapi
  ```