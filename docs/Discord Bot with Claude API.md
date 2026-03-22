# Discord Bot with Claude API - Complete Media Server Integration Guide

## Table of Contents
1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Architecture](#architecture)
4. [Step-by-Step Setup](#step-by-step-setup)
5. [Code Implementation](#code-implementation)
6. [Security Best Practices](#security-best-practices)
7. [Deployment](#deployment)
8. [Usage Examples](#usage-examples)
9. [Troubleshooting](#troubleshooting)

---

## Overview

This guide walks you through creating a Discord bot that integrates with Anthropic's Claude API and runs on your media server. The bot allows you to:

- Analyze server logs via Claude directly in Discord
- Query system information (disk, memory, CPU)
- Execute read-only diagnostic commands
- Maintain conversation history for context-aware responses
- Extend capabilities with custom tools

### Key Benefits

- **Local Execution**: Bot runs on your media server for direct access to files and commands
- **AI-Powered Analysis**: Claude analyzes logs and provides intelligent insights
- **Discord Integration**: Access your server through familiar Discord interface
- **Tool Use**: Claude can execute multiple tools in sequence to solve problems
- **Conversation History**: Claude remembers context across multiple messages

---

## Prerequisites

### On Your Media Server

- Python 3.8 or higher
- `pip` package manager
- SSH access for remote setup
- Ability to install system packages (if needed)

### External Accounts Required

1. **Discord Developer Portal** - To create and configure your bot
2. **Anthropic Console** - To get Claude API key (requires credit)
3. **GitHub** (optional) - For version control

### Estimated Costs

- Claude API: ~$0.03 per 1K input tokens, ~$0.15 per 1K output tokens
- Discord bot: Free
- Server resources: Minimal (bot uses ~50-100MB RAM)

---

## Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                    Discord Server                            │
│                   #media-logs Channel                        │
└────────────────────────┬────────────────────────────────────┘
                         │ (Discord API)
                         │
        ┌────────────────▼────────────────┐
        │    Discord Bot                  │
        │   (Running on Media Server)     │
        │                                 │
        │  - Listens for "Claude ..."     │
        │  - Formats messages             │
        │  - Manages conversation history │
        └────────────────┬────────────────┘
                         │ (Anthropic API)
                         │
        ┌────────────────▼────────────────┐
        │      Claude API                 │
        │   (Tool Use / Function Calling) │
        └────────────────┬────────────────┘
                         │
        ┌────────────────▼────────────────┐
        │   Server Tools & Resources      │
        │                                 │
        │  ├─ read_file                   │
        │  ├─ list_directory              │
        │  ├─ run_command                 │
        │  └─ get_system_info             │
        │                                 │
        │  ├─ /var/log/*                  │
        │  ├─ /etc/config/*               │
        │  └─ System commands             │
        └─────────────────────────────────┘
```

---

## Step-by-Step Setup

### Phase 1: Create Discord Bot

#### Step 1.1 - Register Bot Application

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application"
3. Name it: "Media Server Claude Bot"
4. Click "Create"

#### Step 1.2 - Create Bot User

1. Go to "Bot" section in left sidebar
2. Click "Add Bot"
3. Under "TOKEN", click "Copy"
4. Save this token in a safe place (you'll need it for `.env`)

#### Step 1.3 - Enable Required Intents

1. In Bot settings, scroll to "Privileged Gateway Intents"
2. Enable:
   - ✅ Message Content Intent
   - ✅ Server Members Intent (optional)
3. Click "Save Changes"

#### Step 1.4 - Set Bot Permissions

1. Go to "OAuth2" → "URL Generator"
2. Select scopes:
   - ✅ bot
3. Select permissions:
   - ✅ Send Messages
   - ✅ Read Messages/View Channels
   - ✅ Read Message History
   - ✅ Manage Messages (optional, for cleanup)
4. Copy the generated URL

#### Step 1.5 - Invite Bot to Your Server

1. Paste the URL from Step 1.4 into browser
2. Select your Discord server
3. Click "Authorize"
4. Complete CAPTCHA
5. Bot will appear in your server's member list

### Phase 2: Get Claude API Key

1. Go to [Anthropic Console](https://console.anthropic.com)
2. Create account or sign in
3. Go to "API Keys" section
4. Click "Create Key"
5. Copy the key
6. **Go to "Billing"** and add a payment method + credit (minimum recommended: $5)
7. Save the API key securely

### Phase 3: Set Up Server Directory

On your media server, create the bot directory:
```bash
# SSH into your media server
ssh user@media-server

# Create bot directory
mkdir -p /opt/discord-bot
cd /opt/discord-bot

# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Create directories
mkdir -p logs
```

### Phase 4: Create Configuration Files

#### Step 4.1 - requirements.txt

Create `/opt/discord-bot/requirements.txt`:
```
discord.py==2.3.2
python-dotenv==1.0.0
anthropic==0.25.0
```

#### Step 4.2 - .env File

Create `/opt/discord-bot/.env`:
```bash
DISCORD_BOT_TOKEN=your_discord_bot_token_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
ALLOWED_USERS=user1#1234,user2#5678
LOG_LEVEL=INFO
```

**SECURITY**: Restrict file permissions:
```bash
chmod 600 /opt/discord-bot/.env
```

#### Step 4.3 - Install Dependencies
```bash
cd /opt/discord-bot
source venv/bin/activate
pip install -r requirements.txt
```

---

## Code Implementation

### Main Bot File: bot.py

Create `/opt/discord-bot/bot.py`:
```python
import discord
import os
import json
import subprocess
from discord.ext import commands
from dotenv import load_dotenv
import anthropic
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()

BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
ALLOWED_USERS = os.getenv('ALLOWED_USERS', '').split(',') if os.getenv('ALLOWED_USERS') else []

if not BOT_TOKEN or not ANTHROPIC_API_KEY:
    raise ValueError("Missing DISCORD_BOT_TOKEN or ANTHROPIC_API_KEY in .env file")

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# Store conversation history per user (max 20 messages per user)
conversation_history = {}
MAX_HISTORY_PER_USER = 20

# Define tools Claude can use
TOOLS = [
    {
        "name": "read_file",
        "description": "Read the contents of a file on the server. Useful for analyzing logs.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The full path to the file to read (e.g., /var/log/syslog)"
                },
                "lines": {
                    "type": "integer",
                    "description": "Number of lines to read from the end (optional, default: all)"
                }
            },
            "required": ["file_path"]
        }
    },
    {
        "name": "list_directory",
        "description": "List files and directories in a server folder",
        "input_schema": {
            "type": "object",
            "properties": {
                "directory_path": {
                    "type": "string",
                    "description": "The directory path to list"
                }
            },
            "required": ["directory_path"]
        }
    },
    {
        "name": "run_command",
        "description": "Execute a read-only shell command on the server",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The command to run (e.g., 'ps aux', 'df -h', 'systemctl status plex')"
                }
            },
            "required": ["command"]
        }
    },
    {
        "name": "get_system_info",
        "description": "Get current system information including disk usage, memory, CPU, and uptime",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "search_logs",
        "description": "Search for specific text in a log file",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the log file"
                },
                "search_term": {
                    "type": "string",
                    "description": "Text to search for"
                },
                "context_lines": {
                    "type": "integer",
                    "description": "Lines of context before/after match (default: 2)"
                }
            },
            "required": ["file_path", "search_term"]
        }
    }
]

# ============================================================================
# TOOL IMPLEMENTATIONS
# ============================================================================

def read_file(file_path: str, lines: int = None) -> str:
    """Read file contents (max 10KB for safety)"""
    try:
        # Security: Check file path is allowed
        if not is_path_allowed(file_path):
            return f"Access denied: {file_path}"
        
        with open(file_path, 'r') as f:
            if lines:
                # Read last N lines
                all_lines = f.readlines()
                content = ''.join(all_lines[-lines:])
            else:
                content = f.read(10000)
        
        logger.info(f"Read file: {file_path}")
        return content if content else "(empty file)"
    except FileNotFoundError:
        return f"File not found: {file_path}"
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {str(e)}")
        return f"Error reading file: {str(e)}"

def list_directory(directory_path: str) -> str:
    """List directory contents"""
    try:
        if not is_path_allowed(directory_path):
            return f"Access denied: {directory_path}"
        
        items = os.listdir(directory_path)
        formatted_items = []
        for item in items:
            full_path = os.path.join(directory_path, item)
            if os.path.isdir(full_path):
                formatted_items.append(f"📁 {item}/")
            else:
                formatted_items.append(f"📄 {item}")
        
        logger.info(f"Listed directory: {directory_path}")
        return "\\n".join(formatted_items) if formatted_items else "(empty directory)"
    except Exception as e:
        logger.error(f"Error listing directory {directory_path}: {str(e)}")
        return f"Error listing directory: {str(e)}"

def run_command(command: str) -> str:
    """Execute safe commands (read-only)"""
    # Whitelist of allowed commands for safety
    allowed_prefixes = [
        'ps ', 'df ', 'du ', 'ls ', 'cat ', 'tail ', 'head ', 'grep ',
        'systemctl status', 'systemctl is-active', 'journalctl',
        'docker ps', 'docker stats', 'free ', 'uptime', 'whoami',
        'date', 'hostname', 'uname '
    ]
    
    # Check if command is allowed
    cmd_lower = command.strip().lower()
    is_allowed = any(cmd_lower.startswith(prefix) for prefix in allowed_prefixes)
    
    if not is_allowed:
        logger.warning(f"Command blocked: {command}")
        return "❌ Command not allowed. Only read-only diagnostic commands are permitted."
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        output = result.stdout + result.stderr
        logger.info(f"Executed command: {command}")
        return output[:2000] if output else "(no output)"
    except subprocess.TimeoutExpired:
        logger.warning(f"Command timeout: {command}")
        return "⏱️ Command timed out (30 second limit)"
    except Exception as e:
        logger.error(f"Error running command {command}: {str(e)}")
        return f"Error running command: {str(e)}"

def get_system_info() -> str:
    """Get system information"""
    try:
        info_parts = []
        
        # Disk usage
        df_output = subprocess.run('df -h', shell=True, capture_output=True, text=True).stdout
        info_parts.append("📊 **Disk Usage:**\\n" + df_output)
        
        # Memory
        mem_output = subprocess.run('free -h', shell=True, capture_output=True, text=True).stdout
        info_parts.append("\\n💾 **Memory:**\\n" + mem_output)
        
        # CPU
        if os.path.exists('/proc/cpuinfo'):
            cpu_count = subprocess.run("grep -c processor /proc/cpuinfo", shell=True, capture_output=True, text=True).stdout.strip()
            info_parts.append(f"\\n🔧 **CPU Cores:** {cpu_count}")
        
        # Load average
        uptime_output = subprocess.run('uptime', shell=True, capture_output=True, text=True).stdout
        info_parts.append("\\n⏰ **Uptime & Load:**\\n" + uptime_output)
        
        logger.info("Retrieved system info")
        return "\\n".join(info_parts)
    except Exception as e:
        logger.error(f"Error getting system info: {str(e)}")
        return f"Error getting system info: {str(e)}"

def search_logs(file_path: str, search_term: str, context_lines: int = 2) -> str:
    """Search for text in log files"""
    try:
        if not is_path_allowed(file_path):
            return f"Access denied: {file_path}"
        
        result = subprocess.run(
            f"grep -n -C {context_lines} '{search_term}' {file_path}",
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            logger.info(f"Search found '{search_term}' in {file_path}")
            return result.stdout[:2000]
        else:
            return f"No matches found for '{search_term}' in {file_path}"
    except Exception as e:
        logger.error(f"Error searching logs: {str(e)}")
        return f"Error searching logs: {str(e)}"

def is_path_allowed(path: str) -> bool:
    """Check if path access is allowed"""
    allowed_dirs = [
        '/var/log',
        '/var/spool/cron',
        '/home',
        '/opt',
        '/etc'
    ]
    
    abs_path = os.path.abspath(path)
    return any(abs_path.startswith(allowed_dir) for allowed_dir in allowed_dirs)

# ============================================================================
# PROCESS TOOL CALLS
# ============================================================================

def process_tool_call(tool_name: str, tool_input: dict) -> str:
    """Process tool calls from Claude"""
    if tool_name == "read_file":
        return read_file(tool_input["file_path"], tool_input.get("lines"))
    elif tool_name == "list_directory":
        return list_directory(tool_input["directory_path"])
    elif tool_name == "run_command":
        return run_command(tool_input["command"])
    elif tool_name == "get_system_info":
        return get_system_info()
    elif tool_name == "search_logs":
        return search_logs(
            tool_input["file_path"],
            tool_input["search_term"],
            tool_input.get("context_lines", 2)
        )
    else:
        logger.warning(f"Unknown tool: {tool_name}")
        return f"Unknown tool: {tool_name}"

# ============================================================================
# DISCORD BOT EVENTS
# ============================================================================

@bot.event
async def on_ready():
    logger.info(f'✅ Bot logged in as {bot.user.name}')
    logger.info(f'✅ Bot ID: {bot.user.id}')
    print(f'✅ Bot is ready!')

@bot.event
async def on_message(message):
    # Ignore bot's own messages
    if message.author == bot.user:
        return
    
    # Check if message starts with "Claude"
    if not message.content.startswith('Claude'):
        return
    
    user_id = message.author.id
    user_name = message.author.name
    
    # Optional: Check user permissions
    if ALLOWED_USERS and user_name not in ALLOWED_USERS:
        logger.warning(f"Unauthorized user attempted access: {user_name}")
        await message.reply("❌ You don't have permission to use this bot.")
        return
    
    # Extract user message
    user_message = message.content[len('Claude'):].strip()
    
    if not user_message:
        await message.reply("Usage: `Claude [your question]`")
        return
    
    logger.info(f"Message from {user_name}: {user_message[:100]}")
    
    # Initialize conversation history for user
    if user_id not in conversation_history:
        conversation_history[user_id] = []
    
    # Show typing indicator
    async with message.channel.typing():
        try:
            # Add user message to history
            conversation_history[user_id].append({
                "role": "user",
                "content": user_message
            })
            
            # Keep history under limit
            if len(conversation_history[user_id]) > MAX_HISTORY_PER_USER:
                conversation_history[user_id] = conversation_history[user_id][-MAX_HISTORY_PER_USER:]
            
            # Initial request to Claude with tools
            response = client.messages.create(
                model="claude-opus-4-1",
                max_tokens=2048,
                tools=TOOLS,
                messages=conversation_history[user_id],
                system="You are a helpful system administrator assistant. You have access to server tools to help analyze logs, check system status, and diagnose issues. Be concise and clear in your responses."
            )
            
            # Handle tool use loop
            tool_use_count = 0
            max_iterations = 5
            
            while response.stop_reason == "tool_use" and tool_use_count < max_iterations:
                tool_use_count += 1
                
                # Find tool use blocks
                tool_use_blocks = [block for block in response.content if block.type == "tool_use"]
                
                tool_results = []
                for tool_use in tool_use_blocks:
                    logger.info(f"Tool call: {tool_use.name}")
                    
                    # Execute tool
                    tool_result = process_tool_call(tool_use.name, tool_use.input)
                    
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use.id,
                        "content": tool_result
                    })
                    
                    # Send progress update to Discord
                    status_msg = f"🔧 **{tool_use.name}**"
                    preview = tool_result[:150].replace('\\n', ' ')
                    if len(tool_result) > 150:
                        preview += "..."
                    
                    await message.channel.send(f"{status_msg}\\n```\\n{preview}\\n```")
                
                # Add assistant response and tool results to history
                conversation_history[user_id].append({
                    "role": "assistant",
                    "content": response.content
                })
                conversation_history[user_id].append({
                    "role": "user",
                    "content": tool_results
                })
                
                # Get next response from Claude
                response = client.messages.create(
                    model="claude-opus-4-1",
                    max_tokens=2048,
                    tools=TOOLS,
                    messages=conversation_history[user_id]
                )
            
            # Extract and send final text response
            final_text = ""
            for block in response.content:
                if hasattr(block, 'text'):
                    final_text += block.text
            
            if final_text:
                # Add to conversation history
                conversation_history[user_id].append({
                    "role": "assistant",
                    "content": final_text
                })
                
                logger.info(f"Response sent to {user_name}")
                
                # Send response to Discord (split if too long)
                if len(final_text) > 1900:
                    pages = [final_text[i:i+1900] for i in range(0, len(final_text), 1900)]
                    for i, page in enumerate(pages):
                        page_num = f" (Page {i+1}/{len(pages)})" if len(pages) > 1 else ""
                        await message.channel.send(f"```\\n{page}\\n```{page_num}")
                else:
                    await message.channel.send(f"```\\n{final_text}\\n```")
            else:
                await message.channel.send("No response generated.")
        
        except anthropic.APIError as e:
            logger.error(f"Claude API error: {str(e)}")
            await message.channel.send(f"❌ Claude API Error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            await message.channel.send(f"❌ Unexpected error: {str(e)}")

# ============================================================================
# RUN BOT
# ============================================================================

if __name__ == "__main__":
    try:
        logger.info("Starting Discord bot...")
        bot.run(BOT_TOKEN)
    except Exception as e:
        logger.error(f"Failed to start bot: {str(e)}")
        raise
```

---

## Security Best Practices

### 1. File Permissions
```bash
# Restrict .env file
chmod 600 /opt/discord-bot/.env

# Restrict bot directory
chmod 700 /opt/discord-bot

# Make logs directory
chmod 755 /opt/discord-bot/logs
```

### 2. Command Whitelisting

Only safe, read-only commands are allowed. The whitelist includes:
- `ps` - process listing
- `df` - disk usage
- `du` - directory usage
- `ls` - file listing
- `cat`, `tail`, `head` - file reading
- `grep` - text search
- `systemctl status` - service status
- `journalctl` - system logs
- `docker ps`, `docker stats` - container info
- `free` - memory info
- `uptime` - system uptime

### 3. Path Restrictions

Only these directories are accessible:
- `/var/log` - system logs
- `/var/spool/cron` - cron jobs
- `/home` - user directories
- `/opt` - application files
- `/etc` - configuration files

### 4. Discord User Control

Add allowed users to `.env`:
```
ALLOWED_USERS=yourname#1234,friend#5678
```

### 5. Input Sanitization

- File paths are checked against whitelist
- Commands are matched against allowed prefixes
- Tool inputs are validated before execution
- Long outputs are truncated to 2000 characters

### 6. Logging & Audit Trail

All actions are logged to `logs/bot.log`:
```bash
tail -f /opt/discord-bot/logs/bot.log
```

Monitor for suspicious activity.

---

## Deployment

### Option 1: Manual Start (Testing)
```bash
cd /opt/discord-bot
source venv/bin/activate
python3 bot.py
```

### Option 2: systemd Service (Production)

Create `/etc/systemd/system/discord-claude-bot.service`:
```ini
[Unit]
Description=Discord Claude Bot for Media Server
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=media
Group=media
WorkingDirectory=/opt/discord-bot
Environment="PATH=/opt/discord-bot/venv/bin"
Environment="PYTHONUNBUFFERED=1"
ExecStart=/opt/discord-bot/venv/bin/python3 /opt/discord-bot/bot.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=discord-bot

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
# Reload systemd daemon
sudo systemctl daemon-reload

# Enable on boot
sudo systemctl enable discord-claude-bot

# Start service
sudo systemctl start discord-claude-bot

# Check status
sudo systemctl status discord-claude-bot

# View logs
journalctl -u discord-claude-bot -f
```

### Option 3: Docker Deployment

Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    grep \\
    coreutils \\
    procps \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot
COPY bot.py .
COPY .env .

# Run bot
CMD ["python3", "bot.py"]
```

Build and run:
```bash
docker build -t discord-claude-bot .
docker run -d \\
  --name claude-bot \\
  --restart unless-stopped \\
  -v /var/log:/var/log:ro \\
  discord-claude-bot
```

### Option 4: Docker Compose

Create `docker-compose.yml`:
```yaml
version: '3.8'

services:
  discord-bot:
    build: .
    container_name: discord-claude-bot
    restart: unless-stopped
    environment:
      - DISCORD_BOT_TOKEN=${DISCORD_BOT_TOKEN}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - LOG_LEVEL=INFO
    volumes:
      - /var/log:/var/log:ro
      - ./logs:/app/logs
    networks:
      - default

networks:
  default:
    driver: bridge
```

Run with:
```bash
docker-compose up -d
docker-compose logs -f
```

---

## Usage Examples

### Example 1: Analyze Plex Server Logs
```
Claude What errors are in the Plex server logs from the last hour?
```

Claude will:
1. Use `read_file` to get Plex logs
2. Search for errors
3. Analyze and explain issues

### Example 2: Check System Health
```
Claude Is the server running healthy? Check disk, memory, and CPU.
```

Claude will:
1. Call `get_system_info`
2. Analyze metrics
3. Report any issues or bottlenecks

### Example 3: Monitor Services
```
Claude Which services are running? Are there any crashed services?
```

Claude will:
1. Execute `systemctl` commands
2. Check service status
3. Alert about failures

### Example 4: Troubleshoot Issues
```
Claude I'm getting 'No space left on device' errors. Where is the disk full?
```

Claude will:
1. Use `run_command` to find large files
2. Identify disk usage
3. Suggest cleanup locations

### Example 5: Continuous Monitoring
```
Claude Show me any errors from the last 24 hours across all logs
```

Claude will:
1. Search multiple log files
2. Aggregate errors
3. Provide summary

---

## Troubleshooting

### Bot Not Responding

1. Check bot is running:
```bash
ps aux | grep bot.py
```

2. Check logs:
```bash
tail -f /opt/discord-bot/logs/bot.log
```

3. Verify bot token in Discord:
   - Check bot is in your server
   - Check bot has correct permissions
   - Verify token is correct

### API Errors

**Error: "Invalid API key"**
- Verify API key in `.env`
- Check API key hasn't expired
- Test key in Anthropic console

**Error: "Rate limited"**
- Wait a few minutes
- Check account quota
- Add more credits if needed

**Error: "Token invalid"**
- Regenerate Discord bot token
- Update `.env` file
- Restart bot

### Permission Issues

**Error: "Permission denied" on files**
- Check file permissions
- Verify bot user can read files
- Check path is in allowed list

**Error: "Command not allowed"**
- Command is not in whitelist
- Add to allowed_prefixes if needed
- Only read-only commands allowed

### High Memory Usage

- Reduce `MAX_HISTORY_PER_USER` in bot.py
- Reduce `max_tokens` in Claude API call
- Clear logs periodically

### Network Issues
```bash
# Check connection to Discord
ping discord.com

# Check connection to Anthropic
ping api.anthropic.com

# Check DNS
nslookup discord.com
```

---

## Advanced Customization

### Add Email Notifications

Modify bot to send email alerts for critical issues:
```python
import smtplib
from email.mime.text import MIMEText

def send_alert_email(subject, message):
    # Implementation here
    pass
```

### Add Database Logging

Store all queries and responses in a database:
```python
import sqlite3

def log_to_db(user_id, query, response):
    # Implementation here
    pass
```

### Add Response Webhooks

Send critical findings to external systems:
```python
import requests

def webhook_alert(title, message):
    # Send to Slack, PagerDuty, etc.
    pass
```

### Create Custom Tools

Add tools specific to your setup:
```python
{
    "name": "restart_plex",
    "description": "Restart the Plex service",
    "input_schema": { ... }
}
```

---

## Monitoring & Maintenance

### Daily Checks
```bash
# Check bot is running
systemctl status discord-claude-bot

# Check recent logs
journalctl -u discord-claude-bot -n 50

# Verify Claude API calls
tail -20 /opt/discord-bot/logs/bot.log | grep "Tool call"
```

### Weekly Tasks
```bash
# Rotate logs
logrotate -f /etc/logrotate.d/discord-bot

# Check disk usage
du -sh /opt/discord-bot/logs

# Review error patterns
grep "ERROR" /opt/discord-bot/logs/bot.log | tail -20
```

### Monthly Maintenance
```bash
# Update dependencies
pip install --upgrade -r requirements.txt

# Backup configuration
tar -czf discord-bot-backup-$(date +%Y%m%d).tar.gz /opt/discord-bot/.env

# Review allowed commands/paths
vim /opt/discord-bot/bot.py  # Check TOOLS and allowed_dirs
```

---

## Cost Estimation

Claude API pricing (as of January 2025):

| Model | Input | Output |
|-------|-------|--------|
| Claude 3.5 Sonnet | $0.003/1K tokens | $0.015/1K tokens |
| Claude Opus 4.1 | $0.015/1K tokens | $0.075/1K tokens |

### Typical Usage

- **Small log analysis** (1-5KB): ~$0.01-0.05
- **System diagnostics** (multiple tools): ~$0.05-0.15
- **Large log analysis** (50KB+): ~$0.20-0.50
- **Daily monitoring** (5-10 queries): ~$0.25-0.50

**Budget Recommendation**: $5-20/month for typical media server monitoring

---

## Next Steps

1. ✅ Create Discord bot
2. ✅ Get Claude API key with credit
3. ✅ Set up server directory
4. ✅ Create configuration files
5. ✅ Deploy bot with systemd
6. ✅ Test with simple queries
7. ✅ Configure allowed users
8. ✅ Set up log rotation
9. ✅ Monitor and optimize

---

## Support & Resources

- [Discord.py Documentation](https://discordpy.readthedocs.io/)
- [Anthropic Claude API Docs](https://docs.anthropic.com)
- [Python subprocess Documentation](https://docs.python.org/3/library/subprocess.html)
- [systemd Service Documentation](https://www.freedesktop.org/software/systemd/man/systemd.service.html)

---

## License

This bot implementation is provided as-is. Use at your own risk.

---

*Last Updated: January 2025*
*Discord Claude Bot with Server Integration Guide*