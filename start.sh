#!/bin/bash
set -e

VENV=".venv"
SOURCES="/etc/apt/sources.list"

echo "[*] Configuring Debian Bullseye archive repository..."

# Back up existing sources.list
if [ ! -f "${SOURCES}.bak" ]; then
    sudo cp "$SOURCES" "${SOURCES}.bak"
fi

# Debian Bullseye archive
sudo tee "$SOURCES" > /dev/null <<EOF
deb http://archive.debian.org/debian bullseye main non-free
EOF

echo "[*] Updating package lists..."
sudo apt-get \
    -o Acquire::Check-Valid-Until=false \
    update

echo "[*] Installing Python tooling..."
sudo apt-get \
    -o Acquire::Check-Valid-Until=false \
    install -y python3-pip python3-venv

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV" ]; then
    echo "[*] Creating virtual environment..."
    python3 -m venv "$VENV"
fi

echo "[*] Activating virtual environment..."
source "$VENV/bin/activate"

echo "[*] Installing Python requirements..."
python -m pip install -r requirements.txt

echo "[*] Starting app..."
python -m app