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
        return "\n".join(formatted_items) if formatted_items else "(empty directory)"
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
        'date', 'hostname', 'uname ', 'docker compose ps', 'docker compose logs'
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
        info_parts.append("📊 **Disk Usage:**\n" + df_output)

        # Memory
        mem_output = subprocess.run('free -h', shell=True, capture_output=True, text=True).stdout
        info_parts.append("\n💾 **Memory:**\n" + mem_output)

        # CPU
        if os.path.exists('/proc/cpuinfo'):
            cpu_count = subprocess.run("grep -c processor /proc/cpuinfo", shell=True, capture_output=True, text=True).stdout.strip()
            info_parts.append(f"\n🔧 **CPU Cores:** {cpu_count}")

        # Load average
        uptime_output = subprocess.run('uptime', shell=True, capture_output=True, text=True).stdout
        info_parts.append("\n⏰ **Uptime & Load:**\n" + uptime_output)

        logger.info("Retrieved system info")
        return "\n".join(info_parts)
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
        '/etc',
        '/mnt'
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
                system="""You are a helpful system administrator assistant for a Docker-based media server. You have access to server tools to help analyze logs, check system status, and diagnose issues. Be concise and clear in your responses.

MEDIA SERVER LOG LOCATIONS (all in /opt/mediaserver/):
- Sonarr: /opt/mediaserver/sonarr/logs/ (sonarr.txt.log or logs folder)
- Radarr: /opt/mediaserver/radarr/logs/ (radarr.txt.log or logs folder)
- SABnzbd: /opt/mediaserver/sabnzbd/logs/ (sabnzbd.log)
- Prowlarr: /opt/mediaserver/prowlarr/logs/ (prowlarr.txt.log)
- Jellyfin: /opt/mediaserver/jellyfin/logs/
- Plex: Check host system logs in /var/log/plex or docker compose logs plex
- Bazarr: /opt/mediaserver/bazarr/logs/
- Overseerr: /opt/mediaserver/overseerr/logs/
- Jellyseerr: /opt/mediaserver/jellyseerr/logs/
- Tautulli: /opt/mediaserver/tautulli/Tautulli.log
- LoggiFly: /opt/mediaserver/loggifly/logs/ or docker compose logs loggifly

DOCKER COMPOSE:
- All services run as Docker containers in /opt/mediaserver/
- Use 'docker compose ps' to check service status
- Use 'docker compose logs <service-name>' to see live logs

When analyzing logs:
1. First check the correct log file location above
2. Read the appropriate log file for the service being asked about
3. Look for ERROR, WARNING, and FAILED patterns
4. Provide a summary of what went wrong and suggested fixes
5. Ask clarifying questions if needed"""
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
                    preview = tool_result[:150].replace('\n', ' ')
                    if len(tool_result) > 150:
                        preview += "..."

                    await message.channel.send(f"{status_msg}\n```\n{preview}\n```")

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
                        await message.channel.send(f"```\n{page}\n```{page_num}")
                else:
                    await message.channel.send(f"```\n{final_text}\n```")
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
