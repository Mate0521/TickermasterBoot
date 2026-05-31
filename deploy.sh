#!/bin/bash
# ==============================================================
# Script de despliegue para TicketmasterBot en Oracle Cloud Free Tier
# ==============================================================
# Uso:
#   1. Crear VM en Oracle Cloud (Ubuntu 22.04/24.04, mínimo 1 OCPU, 1GB RAM)
#   2. Conectarte por SSH
#   3. Copiar y pegar esto en la terminal:
#
#      curl -fsSL https://raw.githubusercontent.com/Mate0521/TickermasterBoot/main/deploy.sh | bash
#
#   4. Editar .env con tus credenciales:
#      nano ~/ticketmaster/.env
#
#   5. Iniciar el bot:
#      sudo systemctl start ticketmasterbot

set -e

echo "=== TicketmasterBot - Instalacion en Oracle Cloud ==="

# Variables
USER_HOME=$(eval echo ~$SUDO_USER)
PROJECT_DIR="$USER_HOME/ticketmaster"
REPO_URL="https://github.com/Mate0521/TickermasterBoot.git"

# 1. Instalar dependencias del sistema
echo "[1/6] Instalando dependencias del sistema..."
sudo apt update -qq
sudo apt install -y -qq python3 python3-pip python3-venv git curl

# 2. Clonar repositorio
echo "[2/6] Clonando repositorio..."
if [ -d "$PROJECT_DIR" ]; then
    cd "$PROJECT_DIR" && git pull
else
    git clone "$REPO_URL" "$PROJECT_DIR"
fi

# 3. Crear entorno virtual e instalar dependencias Python
echo "[3/6] Instalando dependencias Python..."
cd "$PROJECT_DIR"
python3 -m venv venv
source venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet requests python-dotenv playwright beautifulsoup4 lxml
playwright install chromium
playwright install-deps chromium

# 4. Crear archivo .env (placeholder)
echo "[4/6] Creando .env de ejemplo..."
if [ ! -f ".env" ]; then
    cat > .env << 'EOF'
TELEGRAM_TOKEN=
TELEGRAM_CHAT_ID=
TICKETMASTER_API_KEY=
TICKETMASTER_EVENT_ID=
EOF
    echo "  !!! IMPORTANTE: edita ~/ticketmaster/.env con tus credenciales !!!"
fi

# 5. Crear archivo de log (con rotacion)
echo "[5/6] Configurando logrotate..."
sudo tee /etc/logrotate.d/ticketmasterbot > /dev/null << 'EOF'
/home/ubuntu/ticketmaster/ticketmaster.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
}
EOF

# 6. Crear servicio systemd
echo "[6/6] Instalando servicio systemd..."
sudo tee /etc/systemd/system/ticketmasterbot.service > /dev/null << 'SERVICE'
[Unit]
Description=TicketmasterBot - Monitoreo híbrido BTS
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/ticketmaster
ExecStart=/home/ubuntu/ticketmaster/venv/bin/python /home/ubuntu/ticketmaster/main.py
Restart=always
RestartSec=30
StandardOutput=append:/home/ubuntu/ticketmaster/ticketmaster.log
StandardError=append:/home/ubuntu/ticketmaster/ticketmaster.log

[Install]
WantedBy=multi-user.target
SERVICE

sudo systemctl daemon-reload
sudo systemctl enable ticketmasterbot

echo ""
echo "========================================================"
echo "  Instalacion completada."
echo ""
echo "  ANTES DE INICIAR:"
echo "    nano ~/ticketmaster/.env"
echo "    (pega tus credenciales de Telegram y Ticketmaster)"
echo ""
echo "  Para iniciar:"
echo "    sudo systemctl start ticketmasterbot"
echo ""
echo "  Para ver logs en vivo:"
echo "    journalctl -u ticketmasterbot -f"
echo ""
echo "  Para verificar estado:"
echo "    sudo systemctl status ticketmasterbot"
echo "========================================================"
