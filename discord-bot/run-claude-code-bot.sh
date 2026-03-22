#!/bin/bash
# Script to run the Discord bot with Claude Code integration

# Set working directory
cd /opt/mediaserver/discord-bot

# Activate virtual environment
if [ -f "venv-claude-code/bin/activate" ]; then
    source venv-claude-code/bin/activate
    echo "✓ Activated venv-claude-code"
else
    echo "ERROR: venv-claude-code not found or not set up properly"
    echo "Please run: python3 -m venv venv-claude-code && source venv-claude-code/bin/activate && pip install discord.py python-dotenv pexpect"
    exit 1
fi

# Ensure Claude CLI is in PATH
export PATH="/home/christof21/.npm-global/bin:$PATH"

# Set working directory for Claude Code
export CLAUDE_WORKING_DIR="/opt/mediaserver"

# Run the bot
echo "Starting Discord Claude Code bot..."
echo "Working directory: $CLAUDE_WORKING_DIR"
echo "Claude CLI path: $(which claude)"
echo "Python: $(which python) ($(python --version))"
echo ""

# Check if required packages are installed
python -c "import discord, pexpect, dotenv" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "ERROR: Required Python packages not installed in venv."
    echo "Run: source venv-claude-code/bin/activate && pip install discord.py python-dotenv pexpect"
    exit 1
fi

python bot-claude-code.py
