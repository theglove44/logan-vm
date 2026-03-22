#!/usr/bin/env python3
"""
Discord Bot that runs Claude Code CLI from /opt/mediaserver
Maintains persistent Claude Code session and forwards approval prompts to Discord
"""

import discord
import os
import asyncio
import re
from discord.ext import commands
from dotenv import load_dotenv
import logging
from datetime import datetime
import pexpect
from threading import Thread, Lock
from queue import Queue
import time

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot-claude-code.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()

BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
ALLOWED_USERS = os.getenv('ALLOWED_USERS', '').split(',') if os.getenv('ALLOWED_USERS') else []
CLAUDE_WORKING_DIR = os.getenv('CLAUDE_WORKING_DIR', '/opt/mediaserver')
CLAUDE_MODEL = os.getenv('CLAUDE_MODEL', 'sonnet')  # Default: sonnet (can use 'opus', 'haiku', or full model name)

if not BOT_TOKEN:
    raise ValueError("Missing DISCORD_BOT_TOKEN in .env file")

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.reactions = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Store Claude Code session per Discord channel
claude_sessions = {}
session_lock = Lock()

# Store pending approvals (message_id -> approval_data)
pending_approvals = {}

# System prompt for Claude Code context
SYSTEM_PROMPT = """You are assisting with a media server at /opt/mediaserver.

Key service log locations:
- Sonarr: /opt/mediaserver/sonarr/logs/sonarr.txt
- Radarr: /opt/mediaserver/radarr/logs/radarr.txt
- Prowlarr: /opt/mediaserver/prowlarr/logs/prowlarr.txt
- SABnzbd: /opt/mediaserver/sabnzbd/logs/sabnzbd.log
- Jellyfin: /opt/mediaserver/jellyfin/log/
- Plex: /opt/mediaserver/plex/Library/Application Support/Plex Media Server/Logs/
- Overseerr: /opt/mediaserver/overseerr/logs/overseerr.log
- Homepage: docker compose logs homepage

Docker services: docker compose ps
Docker logs: docker compose logs <service>

Be concise and helpful. Focus on diagnosing issues and providing actionable information.
"""


class ClaudeCodeSession:
    """Manages a persistent Claude Code CLI session"""

    def __init__(self, channel_id, working_dir=CLAUDE_WORKING_DIR):
        self.channel_id = channel_id
        self.working_dir = working_dir
        self.process = None
        self.output_queue = Queue()
        self.reader_thread = None
        self.is_running = False
        self.current_message = None
        self.approval_callback = None

    def start(self):
        """Start the Claude Code CLI process"""
        try:
            logger.info(f"Starting Claude Code session for channel {self.channel_id}")

            # Spawn claude CLI with environment
            claude_cmd = ['claude', '--model', CLAUDE_MODEL]
            self.process = pexpect.spawn(
                ' '.join(claude_cmd),
                cwd=self.working_dir,
                timeout=None,
                encoding='utf-8',
                echo=False,
                env={**os.environ}
            )

            self.is_running = True

            # Start reader thread
            self.reader_thread = Thread(target=self._read_output, daemon=True)
            self.reader_thread.start()

            # Wait for initial prompt
            time.sleep(2)

            # Send system context as first message
            self.send_message(SYSTEM_PROMPT)

            logger.info(f"Claude Code session started for channel {self.channel_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to start Claude Code session: {e}")
            self.is_running = False
            return False

    def _read_output(self):
        """Background thread that reads from Claude Code process"""
        buffer = ""

        while self.is_running and self.process.isalive():
            try:
                # Read with short timeout to allow checking is_running
                char = self.process.read_nonblocking(size=1, timeout=0.1)
                buffer += char

                # Check for complete output patterns
                if self._is_complete_output(buffer):
                    self.output_queue.put(('output', buffer))
                    buffer = ""

            except pexpect.TIMEOUT:
                # No data available, continue
                if buffer:
                    # Send accumulated buffer if we have content
                    self.output_queue.put(('partial', buffer))
                continue

            except pexpect.EOF:
                logger.info("Claude Code process ended")
                self.is_running = False
                break

            except Exception as e:
                logger.error(f"Error reading from Claude Code: {e}")
                break

        # Send any remaining buffer
        if buffer:
            self.output_queue.put(('output', buffer))

    def _is_complete_output(self, text):
        """Check if we have a complete output block"""
        # Look for patterns that indicate end of response
        patterns = [
            r'\n\n$',  # Double newline
            r'Allow\? \(y/n\):',  # Approval prompt
            r'Continue\? \(y/n\):',  # Continue prompt
            r'>\s*$',  # Prompt character
        ]

        for pattern in patterns:
            if re.search(pattern, text):
                return True

        # If buffer is getting large, send it anyway
        if len(text) > 2000:
            return True

        return False

    def send_message(self, message):
        """Send a message to Claude Code"""
        if not self.is_running or not self.process:
            return False

        try:
            logger.info(f"Sending to Claude: {message[:100]}...")
            self.process.sendline(message)
            return True
        except Exception as e:
            logger.error(f"Error sending message to Claude: {e}")
            return False

    def approve(self, approved=True):
        """Send approval response to Claude Code"""
        response = 'y' if approved else 'n'
        return self.send_message(response)

    def get_output(self, timeout=1):
        """Get output from the queue (non-blocking)"""
        outputs = []
        deadline = time.time() + timeout

        while time.time() < deadline:
            try:
                output = self.output_queue.get(timeout=0.1)
                outputs.append(output)
            except:
                break

        return outputs

    def stop(self):
        """Stop the Claude Code session"""
        logger.info(f"Stopping Claude Code session for channel {self.channel_id}")
        self.is_running = False

        if self.process:
            try:
                self.process.sendcontrol('c')
                self.process.sendline('exit')
                self.process.terminate(force=True)
            except:
                pass

        if self.reader_thread:
            self.reader_thread.join(timeout=2)


def get_or_create_session(channel_id):
    """Get existing session or create new one"""
    with session_lock:
        if channel_id not in claude_sessions:
            session = ClaudeCodeSession(channel_id)
            if session.start():
                claude_sessions[channel_id] = session
            else:
                return None
        return claude_sessions.get(channel_id)


def close_session(channel_id):
    """Close a Claude Code session"""
    with session_lock:
        if channel_id in claude_sessions:
            claude_sessions[channel_id].stop()
            del claude_sessions[channel_id]


def is_approval_prompt(text):
    """Check if text contains an approval prompt"""
    approval_patterns = [
        r'Allow\? \(y/n\):',
        r'Continue\? \(y/n\):',
        r'Proceed\? \(y/n\):',
        r'Do you want to.*\? \(y/n\):',
    ]

    for pattern in approval_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


async def send_or_edit_message(channel, message_ref, content):
    """Send new message or edit existing one"""
    # Split long messages
    if len(content) > 1900:
        content = content[:1900] + "\n... (truncated)"

    try:
        if message_ref and message_ref[0]:
            # Edit existing message
            await message_ref[0].edit(content=f"```\n{content}\n```")
        else:
            # Send new message
            msg = await channel.send(f"```\n{content}\n```")
            if message_ref is not None:
                message_ref[0] = msg
            return msg
    except Exception as e:
        logger.error(f"Error sending/editing message: {e}")
        return None


@bot.event
async def on_ready():
    logger.info(f'✅ Bot logged in as {bot.user.name}')
    logger.info(f'✅ Bot ID: {bot.user.id}')
    logger.info(f'✅ Working directory: {CLAUDE_WORKING_DIR}')
    logger.info(f'✅ Model: {CLAUDE_MODEL}')
    print(f'✅ Claude Code Bot is ready!')
    print(f'✅ Using model: {CLAUDE_MODEL}')


@bot.event
async def on_message(message):
    # Ignore bot's own messages
    if message.author == bot.user:
        return

    # Check if message starts with "Claude"
    if not message.content.startswith('Claude'):
        return

    user_name = message.author.name
    channel_id = message.channel.id

    # Optional: Check user permissions
    if ALLOWED_USERS and user_name not in ALLOWED_USERS:
        logger.warning(f"Unauthorized user attempted access: {user_name}")
        await message.reply("❌ You don't have permission to use this bot.")
        return

    # Handle special commands
    user_message = message.content[len('Claude'):].strip()

    if user_message.lower() == 'restart':
        close_session(channel_id)
        await message.reply("🔄 Restarting Claude Code session...")
        return

    if user_message.lower() == 'status':
        session = claude_sessions.get(channel_id)
        if session and session.is_running:
            await message.reply("✅ Claude Code session is running")
        else:
            await message.reply("❌ No active Claude Code session")
        return

    if not user_message:
        await message.reply("Usage: `Claude [your question]`\n"
                          "Special commands: `Claude restart`, `Claude status`")
        return

    logger.info(f"Message from {user_name}: {user_message[:100]}")

    # Get or create Claude Code session
    session = get_or_create_session(channel_id)
    if not session:
        await message.reply("❌ Failed to start Claude Code session")
        return

    # Show typing indicator
    async with message.channel.typing():
        # Send message to Claude Code
        if not session.send_message(user_message):
            await message.reply("❌ Failed to send message to Claude Code")
            return

        # Wait for and collect output
        await asyncio.sleep(1)  # Give Claude time to respond

        accumulated_output = ""
        message_ref = [None]  # Mutable reference for editing

        # Collect outputs for up to 30 seconds
        for _ in range(30):
            outputs = session.get_output(timeout=1)

            if not outputs:
                # No more output, we're done
                if accumulated_output:
                    break
                continue

            for output_type, output_text in outputs:
                accumulated_output += output_text

                # Check if this is an approval prompt
                if is_approval_prompt(output_text):
                    # Send approval prompt to Discord
                    await send_or_edit_message(message.channel, message_ref, accumulated_output)

                    # Add reaction buttons
                    if message_ref[0]:
                        await message_ref[0].add_reaction('✅')
                        await message_ref[0].add_reaction('❌')

                        # Store approval context
                        pending_approvals[message_ref[0].id] = {
                            'session': session,
                            'timestamp': datetime.now()
                        }

                    return  # Wait for user reaction

                # Update Discord message with accumulated output
                if len(accumulated_output) > 100:  # Only update if substantial
                    await send_or_edit_message(message.channel, message_ref, accumulated_output)

            # If we haven't seen any output in a while, stop waiting
            if not outputs:
                break

        # Send final output
        if accumulated_output:
            await send_or_edit_message(message.channel, message_ref, accumulated_output)
        else:
            await message.reply("⚠️ No response from Claude Code (it may still be processing)")


@bot.event
async def on_reaction_add(reaction, user):
    """Handle approval reactions"""
    # Ignore bot's own reactions
    if user == bot.user:
        return

    message_id = reaction.message.id

    # Check if this is a pending approval
    if message_id not in pending_approvals:
        return

    approval_data = pending_approvals[message_id]
    session = approval_data['session']

    # Check reaction type
    if str(reaction.emoji) == '✅':
        # Approved
        logger.info(f"User {user.name} approved action")
        session.approve(approved=True)
        await reaction.message.reply("✅ Approved - Claude Code is continuing...")

    elif str(reaction.emoji) == '❌':
        # Denied
        logger.info(f"User {user.name} denied action")
        session.approve(approved=False)
        await reaction.message.reply("❌ Denied - Claude Code operation cancelled")

    # Clean up
    del pending_approvals[message_id]

    # Continue collecting output
    await asyncio.sleep(1)

    accumulated_output = ""
    message_ref = [None]

    for _ in range(30):
        outputs = session.get_output(timeout=1)

        if not outputs:
            if accumulated_output:
                break
            continue

        for output_type, output_text in outputs:
            accumulated_output += output_text

            if len(accumulated_output) > 100:
                await send_or_edit_message(reaction.message.channel, message_ref, accumulated_output)

        if not outputs:
            break

    if accumulated_output:
        await send_or_edit_message(reaction.message.channel, message_ref, accumulated_output)


@bot.event
async def on_disconnect():
    """Clean up sessions on disconnect"""
    logger.info("Bot disconnecting, cleaning up sessions...")
    with session_lock:
        for session in claude_sessions.values():
            session.stop()
        claude_sessions.clear()


if __name__ == "__main__":
    try:
        logger.info("Starting Discord Claude Code bot...")
        logger.info(f"Working directory: {CLAUDE_WORKING_DIR}")
        bot.run(BOT_TOKEN)
    except Exception as e:
        logger.error(f"Failed to start bot: {str(e)}")
        raise
