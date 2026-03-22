#!/bin/bash
# One-step installation script for Discord Claude Code bot

echo "================================================"
echo "Discord Claude Code Bot - Installation Script"
echo "================================================"
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "Please run this script as a normal user (not root)"
    exit 1
fi

# Step 1: Install pip if not available
echo "[1/3] Checking Python and pip..."
if ! command -v pip3 &> /dev/null; then
    echo "  Installing pip3..."
    sudo apt update
    sudo apt install -y python3-pip
else
    echo "  ✓ pip3 is installed"
fi

# Step 2: Install Python dependencies
echo ""
echo "[2/3] Installing Python dependencies..."
pip3 install --user discord.py==2.3.2 python-dotenv==1.0.0 pexpect>=4.8.0

# Check installation
echo ""
echo "[3/3] Verifying installation..."
python3 -c "import discord; print('  ✓ discord.py installed')" 2>/dev/null || echo "  ✗ discord.py failed"
python3 -c "import dotenv; print('  ✓ python-dotenv installed')" 2>/dev/null || echo "  ✗ python-dotenv failed"
python3 -c "import pexpect; print('  ✓ pexpect installed')" 2>/dev/null || echo "  ✗ pexpect failed"

# Check Claude CLI
echo ""
if command -v claude &> /dev/null; then
    echo "  ✓ Claude CLI found: $(which claude)"
    echo "  ✓ Version: $(claude --version)"
else
    echo "  ✗ Claude CLI not found in PATH"
    echo "  Note: Make sure 'claude' command is installed"
fi

# Check .env file
echo ""
if [ -f "/opt/mediaserver/discord-bot/.env" ]; then
    if grep -q "DISCORD_BOT_TOKEN" /opt/mediaserver/discord-bot/.env; then
        echo "  ✓ .env file exists with DISCORD_BOT_TOKEN"
    else
        echo "  ⚠ .env file exists but missing DISCORD_BOT_TOKEN"
    fi
else
    echo "  ⚠ .env file not found - you'll need to create it"
    echo "    Copy from: /opt/mediaserver/discord-bot/.env"
fi

echo ""
echo "================================================"
echo "Installation complete!"
echo "================================================"
echo ""
echo "To start the bot:"
echo "  cd /opt/mediaserver/discord-bot"
echo "  ./run-claude-code-bot.sh"
echo ""
echo "For production deployment (systemd):"
echo "  See CLAUDE-CODE-BOT-SETUP.md"
echo ""
