#!/bin/bash
# Quick setup script for Claude Code bot virtual environment

set -e  # Exit on error

echo "================================================"
echo "Claude Code Bot - Virtual Environment Setup"
echo "================================================"
echo ""

cd /opt/mediaserver/discord-bot

# Step 1: Check for python3-venv
echo "[1/4] Checking for python3-venv..."
if ! dpkg -l | grep -q python3-venv; then
    echo "  Installing python3-venv (requires sudo)..."
    sudo apt update
    sudo apt install -y python3-venv python3-pip
else
    echo "  ✓ python3-venv is installed"
fi

# Step 2: Create venv
echo ""
echo "[2/4] Creating virtual environment..."
if [ -d "venv-claude-code" ]; then
    echo "  Removing old venv-claude-code..."
    rm -rf venv-claude-code
fi

python3 -m venv venv-claude-code
echo "  ✓ venv-claude-code created"

# Step 3: Install packages
echo ""
echo "[3/4] Installing Python packages..."
source venv-claude-code/bin/activate
pip install --upgrade pip
pip install "discord.py>=2.4.0" python-dotenv==1.0.0 pexpect>=4.8.0
echo "  ✓ Packages installed"

# Step 4: Verify
echo ""
echo "[4/4] Verifying installation..."
python -c "import discord; print('  ✓ discord.py installed')"
python -c "import dotenv; print('  ✓ python-dotenv installed')"
python -c "import pexpect; print('  ✓ pexpect installed')"

deactivate

echo ""
echo "================================================"
echo "Setup complete!"
echo "================================================"
echo ""
echo "To start the bot:"
echo "  ./run-claude-code-bot.sh"
echo ""
echo "The bot uses venv-claude-code for all dependencies."
echo ""
