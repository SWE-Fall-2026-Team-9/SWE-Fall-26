#!/bin/bash
set -e

VENV=".venv"

echo "[*] Updating package lists..."
sudo apt-get update

echo "[*] Installing Python tooling..."
sudo apt-get install -y python3-pip python3-venv

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

