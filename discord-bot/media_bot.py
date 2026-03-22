#!/usr/bin/env python3
"""
Unified Media Server Discord Bot

- Auto-creates "MEDIA SERVER" category with organized channels
- Receives webhooks from Sonarr/Radarr/Overseerr (via webhook_server.py)
- Claude API chat with 8 diagnostic tools
- Claude Code CLI sessions via pexpect with approval workflow
"""

import discord
from discord.ext import commands
import os
import json
import shlex
import subprocess
import asyncio
import re
import time
import logging
from datetime import datetime
from threading import Lock
from queue import Queue

import aiohttp
import anthropic
import pexpect
from dotenv import load_dotenv

from webhook_server import WebhookServer

# ============================================================================
# LOGGING
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log'),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger('media_bot')

# ============================================================================
# CONFIGURATION
# ============================================================================

load_dotenv()

BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
ALLOWED_USERS = [u.strip() for u in os.getenv('ALLOWED_USERS', '').split(',') if u.strip()]
CLAUDE_MODEL = os.getenv('CLAUDE_MODEL', 'claude-sonnet-4-6')
CLAUDE_CLI_MODEL = os.getenv('CLAUDE_CLI_MODEL', 'sonnet')

# Service API keys
SONARR_API_KEY = os.getenv('SONARR_API_KEY', '')
RADARR_API_KEY = os.getenv('RADARR_API_KEY', '')
SABNZBD_API_KEY = os.getenv('SABNZBD_API_KEY', '')
PROWLARR_API_KEY = os.getenv('PROWLARR_API_KEY', '')
TAUTULLI_API_KEY = os.getenv('TAUTULLI_API_KEY', '')

SERVICE_URLS = {
    'sonarr':   'http://sonarr:8989',
    'radarr':   'http://radarr:7878',
    'sabnzbd':  'http://sabnzbd:8080',
    'prowlarr': 'http://prowlarr:9696',
    'overseerr': 'http://overseerr:5055',
    'plex':     'http://host.docker.internal:32400',
    'tautulli': 'http://tautulli:8181',
    'bazarr':   'http://bazarr:6767',
}

SERVICE_API_KEYS = {
    'sonarr':   SONARR_API_KEY,
    'radarr':   RADARR_API_KEY,
    'sabnzbd':  SABNZBD_API_KEY,
    'prowlarr': PROWLARR_API_KEY,
    'tautulli': TAUTULLI_API_KEY,
}

if not BOT_TOKEN or not ANTHROPIC_API_KEY:
    raise ValueError("Missing DISCORD_BOT_TOKEN or ANTHROPIC_API_KEY")

# ============================================================================
# CHANNEL DEFINITIONS
# ============================================================================

CATEGORY_NAME = "MEDIA SERVER"

CHANNEL_DEFS = {
    'ms-requests':    'Overseerr media requests',
    'ms-downloading': 'Active downloads from Sonarr/Radarr',
    'ms-completed':   'Successfully imported media',
    'ms-attention':   'Failures and items needing manual intervention',
    'ms-system':      'Health checks, updates, and bot status',
    'ms-claude':      'Interactive Claude AI assistant',
}

# ============================================================================
# CLAUDE TOOLS (8 total)
# ============================================================================

TOOLS = [
    # --- Existing 5 ---
    {
        "name": "read_file",
        "description": "Read the contents of a file on the server. Useful for analyzing logs.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Full path to the file to read"},
                "lines": {"type": "integer", "description": "Number of lines to read from the end (optional, default: entire file up to 10 KB)"},
            },
            "required": ["file_path"],
        },
    },
    {
        "name": "list_directory",
        "description": "List files and directories in a server folder",
        "input_schema": {
            "type": "object",
            "properties": {
                "directory_path": {"type": "string", "description": "Directory path to list"},
            },
            "required": ["directory_path"],
        },
    },
    {
        "name": "run_command",
        "description": "Execute a read-only shell command on the server",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The command to run (read-only diagnostics only)"},
            },
            "required": ["command"],
        },
    },
    {
        "name": "get_system_info",
        "description": "Get current system information including disk usage, memory, CPU, and uptime",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "search_logs",
        "description": "Search for specific text in a log file",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to the log file"},
                "search_term": {"type": "string", "description": "Text to search for"},
                "context_lines": {"type": "integer", "description": "Lines of context around each match (default: 2)"},
            },
            "required": ["file_path", "search_term"],
        },
    },
    # --- New 3 ---
    {
        "name": "check_service_status",
        "description": "Check the health and status of a media server service via its API",
        "input_schema": {
            "type": "object",
            "properties": {
                "service": {
                    "type": "string",
                    "description": "Service name",
                    "enum": ["sonarr", "radarr", "sabnzbd", "prowlarr", "overseerr", "plex", "tautulli", "bazarr"],
                },
            },
            "required": ["service"],
        },
    },
    {
        "name": "get_download_queue",
        "description": "Get the current download queue from Sonarr or Radarr with status, progress, and warnings",
        "input_schema": {
            "type": "object",
            "properties": {
                "service": {"type": "string", "enum": ["sonarr", "radarr"]},
            },
            "required": ["service"],
        },
    },
    {
        "name": "retry_download",
        "description": "Trigger a new search for a series (Sonarr) or movie (Radarr) by ID",
        "input_schema": {
            "type": "object",
            "properties": {
                "service": {"type": "string", "enum": ["sonarr", "radarr"]},
                "media_id": {"type": "integer", "description": "Series ID (Sonarr) or Movie ID (Radarr)"},
            },
            "required": ["service", "media_id"],
        },
    },
]

SYSTEM_PROMPT = """You are a helpful system administrator assistant for a Docker-based media server. You have access to server tools to help analyze logs, check system status, diagnose issues, and manage downloads. Be concise and clear.

MEDIA SERVER LOG LOCATIONS (all under /opt/mediaserver/):
- Sonarr: /opt/mediaserver/sonarr/logs/
- Radarr: /opt/mediaserver/radarr/logs/
- SABnzbd: /opt/mediaserver/sabnzbd/logs/
- Prowlarr: /opt/mediaserver/prowlarr/logs/
- Jellyfin: /opt/mediaserver/jellyfin/logs/
- Plex: /opt/mediaserver/plex/config/Library/Application Support/Plex Media Server/Logs/
- Bazarr: /opt/mediaserver/bazarr/logs/
- Overseerr: /opt/mediaserver/overseerr/logs/
- Tautulli: /opt/mediaserver/tautulli/Tautulli.log
- Caddy: /opt/mediaserver/caddy/logs/

DOCKER: All services run as Docker containers in /opt/mediaserver/. Use 'docker compose ps' and 'docker compose logs <service>' for status.

TOOLS (8 available):
- read_file, list_directory, run_command, get_system_info, search_logs (diagnostics)
- check_service_status (query service health APIs)
- get_download_queue (view Sonarr/Radarr download queues)
- retry_download (trigger new search for a series or movie)

When analyzing issues:
1. Check the correct log files for the service
2. Look for ERROR, WARNING, FAILED patterns
3. Use check_service_status for live health info
4. Provide a summary with suggested fixes"""

# ============================================================================
# TOOL IMPLEMENTATIONS (sync helpers)
# ============================================================================

_ALLOWED_DIRS = ('/var/log', '/var/spool/cron', '/home', '/opt', '/etc', '/mnt')


def _is_path_allowed(path: str) -> bool:
    abs_path = os.path.abspath(path)
    return any(abs_path.startswith(d) for d in _ALLOWED_DIRS)


def _read_file(file_path: str, lines: int = None) -> str:
    if not _is_path_allowed(file_path):
        return f"Access denied: {file_path}"
    try:
        with open(file_path, 'r') as f:
            if lines:
                all_lines = f.readlines()
                return ''.join(all_lines[-lines:]) or "(empty file)"
            return f.read(10_000) or "(empty file)"
    except FileNotFoundError:
        return f"File not found: {file_path}"
    except Exception as e:
        return f"Error reading file: {e}"


def _list_directory(directory_path: str) -> str:
    if not _is_path_allowed(directory_path):
        return f"Access denied: {directory_path}"
    try:
        items = []
        for item in sorted(os.listdir(directory_path)):
            full = os.path.join(directory_path, item)
            prefix = "\U0001f4c1" if os.path.isdir(full) else "\U0001f4c4"
            items.append(f"{prefix} {item}")
        return "\n".join(items) or "(empty directory)"
    except Exception as e:
        return f"Error listing directory: {e}"


_ALLOWED_CMD_PREFIXES = [
    'ps ', 'df ', 'du ', 'ls ', 'cat ', 'tail ', 'head ', 'grep ',
    'systemctl status', 'systemctl is-active', 'journalctl',
    'docker ps', 'docker stats', 'free ', 'uptime', 'whoami',
    'date', 'hostname', 'uname ', 'docker compose ps', 'docker compose logs',
]


def _run_command(command: str) -> str:
    cmd_lower = command.strip().lower()
    if not any(cmd_lower.startswith(p) for p in _ALLOWED_CMD_PREFIXES):
        return "\u274c Command not allowed. Only read-only diagnostic commands are permitted."
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        output = result.stdout + result.stderr
        return (output[:2000] if output else "(no output)")
    except subprocess.TimeoutExpired:
        return "\u23f1\ufe0f Command timed out (30s limit)"
    except Exception as e:
        return f"Error: {e}"


def _get_system_info() -> str:
    parts = []
    try:
        parts.append("\U0001f4ca Disk Usage:\n" + subprocess.run('df -h', shell=True, capture_output=True, text=True).stdout)
        parts.append("\n\U0001f4be Memory:\n" + subprocess.run('free -h', shell=True, capture_output=True, text=True).stdout)
        if os.path.exists('/proc/cpuinfo'):
            cores = subprocess.run("grep -c processor /proc/cpuinfo", shell=True, capture_output=True, text=True).stdout.strip()
            parts.append(f"\n\U0001f527 CPU Cores: {cores}")
        parts.append("\n\u23f0 Uptime:\n" + subprocess.run('uptime', shell=True, capture_output=True, text=True).stdout)
    except Exception as e:
        return f"Error: {e}"
    return "\n".join(parts)


def _search_logs(file_path: str, search_term: str, context_lines: int = 2) -> str:
    if not _is_path_allowed(file_path):
        return f"Access denied: {file_path}"
    try:
        cmd = f"grep -n -C {int(context_lines)} {shlex.quote(search_term)} {shlex.quote(file_path)}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return result.stdout[:2000]
        return f"No matches found for '{search_term}' in {file_path}"
    except Exception as e:
        return f"Error: {e}"


# ============================================================================
# ASYNC TOOL IMPLEMENTATIONS (API-based)
# ============================================================================

async def _check_service_status(http_session: aiohttp.ClientSession, service: str) -> str:
    base_url = SERVICE_URLS.get(service)
    if not base_url:
        return f"Unknown service: {service}"

    api_key = SERVICE_API_KEYS.get(service, '')

    endpoints = {
        'sonarr':   ('/api/v3/system/status', {'X-Api-Key': api_key}),
        'radarr':   ('/api/v3/system/status', {'X-Api-Key': api_key}),
        'prowlarr': ('/api/v1/system/status', {'X-Api-Key': api_key}),
        'sabnzbd':  (f'/api?mode=queue&output=json&apikey={api_key}', {}),
        'overseerr': ('/api/v1/status', {}),
        'plex':     ('/identity', {}),
        'tautulli': (f'/api/v2?apikey={api_key}&cmd=status', {}),
        'bazarr':   ('/api/system/status', {'X-Api-Key': api_key}),
    }

    path, headers = endpoints.get(service, ('/', {}))
    url = f"{base_url}{path}"

    try:
        async with http_session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status != 200:
                return f"{service} returned HTTP {resp.status}"
            data = await resp.json()

            if service in ('sonarr', 'radarr', 'prowlarr'):
                return json.dumps({
                    'status': 'healthy',
                    'version': data.get('version', '?'),
                    'startTime': data.get('startTime', '?'),
                }, indent=2)
            elif service == 'sabnzbd':
                q = data.get('queue', {})
                return json.dumps({
                    'status': 'healthy',
                    'speed': q.get('speed', '?'),
                    'remaining': q.get('sizeleft', '?'),
                    'queue_count': q.get('noofslots', 0),
                }, indent=2)
            elif service == 'plex':
                mc = data.get('MediaContainer', {})
                return json.dumps({
                    'status': 'healthy',
                    'version': mc.get('version', '?'),
                }, indent=2)
            else:
                return json.dumps({'status': 'healthy', 'data': str(data)[:500]}, indent=2)
    except asyncio.TimeoutError:
        return f"{service}: timed out"
    except Exception as e:
        return f"Error checking {service}: {e}"


async def _get_download_queue(http_session: aiohttp.ClientSession, service: str) -> str:
    base_url = SERVICE_URLS.get(service)
    api_key = SERVICE_API_KEYS.get(service, '')
    if not base_url or not api_key:
        return f"{service} not configured (missing URL or API key)"

    url = (
        f"{base_url}/api/v3/queue"
        "?page=1&pageSize=20"
        "&includeUnknownSeriesItems=true&includeSeries=true"
        "&includeEpisode=true&includeMovie=true"
    )
    headers = {'X-Api-Key': api_key}

    try:
        async with http_session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status != 200:
                return f"Queue API returned HTTP {resp.status}"
            data = await resp.json()
            records = data.get('records', [])
            if not records:
                return f"No items in {service} queue"

            lines = [f"{service.title()} Queue ({data.get('totalRecords', len(records))} items):"]
            for item in records[:15]:
                title = item.get('title', '?')
                status = item.get('trackedDownloadState', item.get('status', '?'))
                size_left = item.get('sizeleft', 0)
                size_total = item.get('size', 0)
                pct = round((1 - size_left / size_total) * 100, 1) if size_total > 0 else 0
                warnings = item.get('statusMessages', [])
                warn = f" \u26a0\ufe0f {warnings[0].get('title', '')}" if warnings else ""
                lines.append(f"  - {title}: {status} ({pct}%){warn}")

            return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


async def _retry_download(http_session: aiohttp.ClientSession, service: str, media_id: int) -> str:
    base_url = SERVICE_URLS.get(service)
    api_key = SERVICE_API_KEYS.get(service, '')
    if not base_url or not api_key:
        return f"{service} not configured"

    url = f"{base_url}/api/v3/command"
    headers = {'X-Api-Key': api_key, 'Content-Type': 'application/json'}

    if service == 'sonarr':
        payload = {"name": "SeriesSearch", "seriesId": media_id}
    elif service == 'radarr':
        payload = {"name": "MoviesSearch", "movieIds": [media_id]}
    else:
        return f"Unsupported service: {service}"

    try:
        async with http_session.post(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status in (200, 201):
                data = await resp.json()
                return f"Search triggered for {service} media ID {media_id}. Command ID: {data.get('id', '?')}"
            text = await resp.text()
            return f"Failed: HTTP {resp.status} - {text[:200]}"
    except Exception as e:
        return f"Error: {e}"


# ============================================================================
# POSTER CACHE
# ============================================================================

class PosterCache:
    """In-memory cache for poster URLs with 1-hour TTL."""

    def __init__(self):
        self._cache: dict[str, tuple[str, float]] = {}
        self._ttl = 3600

    def get(self, key: str) -> str | None:
        if key in self._cache:
            url, ts = self._cache[key]
            if time.time() - ts < self._ttl:
                return url
            del self._cache[key]
        return None

    def set(self, key: str, url: str):
        self._cache[key] = (url, time.time())

    async def get_poster_url(self, http_session, source, media_id=None, images=None):
        """Get poster URL from cache, webhook payload, or API."""
        cache_key = f"{source}:{media_id}" if media_id else None

        # Check cache
        if cache_key:
            cached = self.get(cache_key)
            if cached:
                return cached

        # Try from webhook payload images
        if images:
            for img in images:
                if img.get('coverType', '').lower() == 'poster':
                    url = img.get('remoteUrl') or img.get('url', '')
                    if url and url.startswith('http'):
                        if cache_key:
                            self.set(cache_key, url)
                        return url

        # Try from API
        if media_id and source in ('sonarr', 'radarr'):
            api_key = SERVICE_API_KEYS.get(source, '')
            base_url = SERVICE_URLS.get(source, '')
            if api_key and base_url:
                resource = 'series' if source == 'sonarr' else 'movie'
                url = f"{base_url}/api/v3/{resource}/{media_id}"
                headers = {'X-Api-Key': api_key}
                try:
                    async with http_session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            for img in data.get('images', []):
                                if img.get('coverType', '').lower() == 'poster':
                                    poster_url = img.get('remoteUrl') or img.get('url', '')
                                    if poster_url and poster_url.startswith('http'):
                                        if cache_key:
                                            self.set(cache_key, poster_url)
                                        return poster_url
                except Exception as e:
                    logger.debug(f"Poster fetch failed for {source}/{media_id}: {e}")

        return None


# ============================================================================
# CLAUDE CODE CLI SESSION
# ============================================================================

class ClaudeCodeSession:
    """Manages a persistent Claude Code CLI session via pexpect."""

    def __init__(self, channel_id, working_dir='/opt/mediaserver'):
        self.channel_id = channel_id
        self.working_dir = working_dir
        self.process = None
        self.output_queue: Queue = Queue()
        self.reader_thread = None
        self.is_running = False

    def start(self):
        try:
            logger.info(f"Starting CLI session for channel {self.channel_id}")
            cmd = f"claude --model {CLAUDE_CLI_MODEL}"
            self.process = pexpect.spawn(
                cmd,
                cwd=self.working_dir,
                timeout=None,
                encoding='utf-8',
                echo=False,
                env={**os.environ},
            )
            self.is_running = True

            from threading import Thread
            self.reader_thread = Thread(target=self._read_output, daemon=True)
            self.reader_thread.start()
            time.sleep(2)
            return True
        except Exception as e:
            logger.error(f"Failed to start CLI session: {e}")
            self.is_running = False
            return False

    def _read_output(self):
        buffer = ""
        while self.is_running and self.process and self.process.isalive():
            try:
                char = self.process.read_nonblocking(size=1, timeout=0.1)
                buffer += char
                if self._is_complete(buffer):
                    self.output_queue.put(('output', buffer))
                    buffer = ""
            except pexpect.TIMEOUT:
                if buffer and len(buffer) > 50:
                    self.output_queue.put(('partial', buffer))
                    buffer = ""
            except pexpect.EOF:
                self.is_running = False
                break
            except Exception:
                break
        if buffer:
            self.output_queue.put(('output', buffer))

    def _is_complete(self, text):
        patterns = [r'\n\n$', r'Allow\? \(y/n\):', r'Continue\? \(y/n\):', r'>\s*$']
        for p in patterns:
            if re.search(p, text):
                return True
        return len(text) > 2000

    def send_message(self, message):
        if not self.is_running or not self.process:
            return False
        try:
            self.process.sendline(message)
            return True
        except Exception:
            return False

    def approve(self, approved=True):
        return self.send_message('y' if approved else 'n')

    def get_output(self, timeout=1):
        outputs = []
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                outputs.append(self.output_queue.get(timeout=0.1))
            except Exception:
                if outputs:
                    break
        return outputs

    def stop(self):
        self.is_running = False
        if self.process:
            try:
                self.process.sendcontrol('c')
                self.process.sendline('exit')
                self.process.terminate(force=True)
            except Exception:
                pass
        if self.reader_thread:
            self.reader_thread.join(timeout=2)


# ============================================================================
# CHANNEL MANAGER
# ============================================================================

class ChannelManager:
    """Finds or creates the MEDIA SERVER category and its channels."""

    def __init__(self):
        self.channels: dict[str, discord.TextChannel] = {}
        self.category = None

    async def setup(self, guild: discord.Guild):
        # Find or create category
        self.category = discord.utils.get(guild.categories, name=CATEGORY_NAME)
        if not self.category:
            try:
                self.category = await guild.create_category(CATEGORY_NAME)
                logger.info(f"Created category: {CATEGORY_NAME}")
            except discord.Forbidden:
                logger.warning(
                    "Missing 'Manage Channels' permission. "
                    "Please re-invite the bot with Manage Channels permission. "
                    "Falling back to scanning existing channels."
                )
                # Fall back: scan all guild channels for matching names
                for name in CHANNEL_DEFS:
                    ch = discord.utils.get(guild.text_channels, name=name)
                    if ch:
                        self.channels[name] = ch
                        logger.info(f"Found existing channel: #{name}")
                return

        # Find or create each channel under the category
        for name, topic in CHANNEL_DEFS.items():
            channel = discord.utils.get(self.category.text_channels, name=name)
            if not channel:
                try:
                    channel = await guild.create_text_channel(
                        name=name, category=self.category, topic=topic,
                    )
                    logger.info(f"Created channel: #{name}")
                except discord.Forbidden:
                    logger.warning(f"Cannot create #{name} - missing permissions")
                    continue
            self.channels[name] = channel

    def get(self, name: str) -> discord.TextChannel | None:
        return self.channels.get(name)


# ============================================================================
# MEDIA BOT
# ============================================================================

class MediaBot:
    def __init__(self):
        intents = discord.Intents.default()
        intents.messages = True
        intents.message_content = True
        intents.reactions = True
        intents.guilds = True

        self.bot = commands.Bot(command_prefix="!", intents=intents)
        self.claude = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        self.channel_mgr = ChannelManager()
        self.poster_cache = PosterCache()
        self.webhook_server: WebhookServer | None = None
        self.http_session: aiohttp.ClientSession | None = None

        # Per-user conversation history
        self.conversation_history: dict[int, list] = {}
        self.MAX_HISTORY = 20

        # CLI sessions (channel_id -> ClaudeCodeSession)
        self.cli_sessions: dict[int, ClaudeCodeSession] = {}
        self.cli_lock = Lock()

        # Pending reaction approvals (message_id -> data)
        self.pending_approvals: dict[int, dict] = {}

        self._register_events()

    # ------------------------------------------------------------------
    # Event registration
    # ------------------------------------------------------------------

    def _register_events(self):
        @self.bot.event
        async def on_ready():
            logger.info(f"Bot logged in as {self.bot.user.name} (ID: {self.bot.user.id})")

            # Only init once (on_ready can fire multiple times on reconnect)
            if self.http_session is None:
                self.http_session = aiohttp.ClientSession()

            if self.bot.guilds:
                guild = self.bot.guilds[0]
                await self.channel_mgr.setup(guild)
                managed = len(self.channel_mgr.channels)
                logger.info(f"Channel setup done in {guild.name}: {managed}/{len(CHANNEL_DEFS)} channels")

                # Start webhook server (only once)
                if self.webhook_server is None:
                    self.webhook_server = WebhookServer(
                        self.channel_mgr, self.poster_cache, self.http_session,
                    )
                    await self.webhook_server.start()
                    logger.info("Webhook server started on port 9999")

                # Send startup embed
                system_ch = self.channel_mgr.get('ms-system')
                if system_ch:
                    embed = discord.Embed(
                        title="\U0001f7e2 Media Bot Online",
                        description="Unified notification & management bot started.",
                        color=0x2ECC71,
                        timestamp=datetime.utcnow(),
                    )
                    embed.add_field(
                        name="Webhook Endpoint",
                        value="`http://discord-claude-bot:9999`",
                        inline=False,
                    )
                    embed.add_field(
                        name="Channels",
                        value=", ".join(f"#{n}" for n in CHANNEL_DEFS),
                        inline=False,
                    )
                    embed.set_footer(text="Media Bot")
                    await system_ch.send(embed=embed)

        @self.bot.event
        async def on_message(message):
            if message.author == self.bot.user:
                return
            if not message.content.startswith('Claude'):
                return

            user_name = message.author.name
            user_id = message.author.id
            channel_id = message.channel.id

            if ALLOWED_USERS and user_name not in ALLOWED_USERS:
                await message.reply("\u274c You don't have permission to use this bot.")
                return

            user_msg = message.content[len('Claude'):].strip()
            if not user_msg:
                await message.reply(
                    "Usage: `Claude [your question]`\n"
                    "Commands: `Claude cli start`, `Claude cli stop`, "
                    "`Claude restart`, `Claude status`"
                )
                return

            msg_lower = user_msg.lower().strip()

            # Special commands
            if msg_lower == 'cli start':
                await self._start_cli(message, channel_id)
                return
            if msg_lower == 'cli stop':
                await self._stop_cli(message, channel_id)
                return
            if msg_lower == 'restart':
                self._close_cli(channel_id)
                self.conversation_history.pop(user_id, None)
                await message.reply("\U0001f504 Session reset. History cleared.")
                return
            if msg_lower == 'status':
                await self._send_status(message, channel_id)
                return

            # Route: CLI mode or API chat
            if channel_id in self.cli_sessions:
                await self._handle_cli_msg(message, channel_id, user_msg)
            else:
                await self._handle_api_chat(message, user_id, user_name, user_msg)

        @self.bot.event
        async def on_reaction_add(reaction, user):
            if user == self.bot.user:
                return
            msg_id = reaction.message.id
            if msg_id not in self.pending_approvals:
                return

            data = self.pending_approvals[msg_id]
            session = data['session']
            emoji = str(reaction.emoji)

            if emoji == '\u2705':
                session.approve(True)
                await reaction.message.reply("\u2705 Approved")
            elif emoji == '\u274c':
                session.approve(False)
                await reaction.message.reply("\u274c Denied")
            else:
                return

            del self.pending_approvals[msg_id]
            await asyncio.sleep(1)
            await self._collect_cli_output(reaction.message.channel, session)

    # ------------------------------------------------------------------
    # CLI session methods
    # ------------------------------------------------------------------

    async def _start_cli(self, message, channel_id):
        with self.cli_lock:
            if channel_id in self.cli_sessions:
                await message.reply("CLI session already active. Use `Claude cli stop` to end it.")
                return

        status_msg = await message.reply("\U0001f504 Starting Claude Code CLI session...")
        session = ClaudeCodeSession(channel_id)

        if await asyncio.to_thread(session.start):
            with self.cli_lock:
                self.cli_sessions[channel_id] = session
            await status_msg.edit(
                content="\u2705 CLI session started. Messages forwarded to Claude Code.\n"
                "Use `Claude cli stop` to return to API chat."
            )
        else:
            await status_msg.edit(content="\u274c Failed to start CLI session.")

    async def _stop_cli(self, message, channel_id):
        self._close_cli(channel_id)
        await message.reply("\u2705 CLI session ended. Back to API chat mode.")

    def _close_cli(self, channel_id):
        with self.cli_lock:
            session = self.cli_sessions.pop(channel_id, None)
            if session:
                session.stop()

    async def _handle_cli_msg(self, message, channel_id, user_msg):
        session = self.cli_sessions.get(channel_id)
        if not session or not session.is_running:
            self._close_cli(channel_id)
            await message.reply("CLI session ended unexpectedly. Use `Claude cli start` to restart.")
            return

        async with message.channel.typing():
            if not session.send_message(user_msg):
                await message.reply("\u274c Failed to send to CLI")
                return
            await asyncio.sleep(1)
            await self._collect_cli_output(message.channel, session)

    async def _collect_cli_output(self, channel, session):
        accumulated = ""
        msg_ref = [None]

        for _ in range(30):
            outputs = await asyncio.to_thread(session.get_output, 1)
            if not outputs:
                if accumulated:
                    break
                continue

            for _, text in outputs:
                accumulated += text

                if self._is_approval_prompt(text):
                    await self._send_or_edit(channel, msg_ref, accumulated)
                    if msg_ref[0]:
                        await msg_ref[0].add_reaction('\u2705')
                        await msg_ref[0].add_reaction('\u274c')
                        self.pending_approvals[msg_ref[0].id] = {
                            'session': session,
                            'timestamp': datetime.now(),
                        }
                    return

                if len(accumulated) > 100:
                    await self._send_or_edit(channel, msg_ref, accumulated)

        if accumulated:
            await self._send_or_edit(channel, msg_ref, accumulated)
        else:
            await channel.send("\u26a0\ufe0f No response from CLI (may still be processing)")

    @staticmethod
    def _is_approval_prompt(text):
        patterns = [
            r'Allow\? \(y/n\):',
            r'Continue\? \(y/n\):',
            r'Proceed\? \(y/n\):',
            r'Do you want to.*\? \(y/n\):',
        ]
        return any(re.search(p, text, re.IGNORECASE) for p in patterns)

    @staticmethod
    async def _send_or_edit(channel, msg_ref, content):
        display = content[:1900] + "\n... (truncated)" if len(content) > 1900 else content
        try:
            if msg_ref[0]:
                await msg_ref[0].edit(content=f"```\n{display}\n```")
            else:
                msg_ref[0] = await channel.send(f"```\n{display}\n```")
        except Exception as e:
            logger.error(f"Error sending/editing message: {e}")

    # ------------------------------------------------------------------
    # Status command
    # ------------------------------------------------------------------

    async def _send_status(self, message, channel_id):
        cli_active = channel_id in self.cli_sessions
        wh_running = self.webhook_server and self.webhook_server.is_running
        channels_ready = len(self.channel_mgr.channels)

        embed = discord.Embed(title="Bot Status", color=0x3498DB)
        embed.add_field(name="Mode", value="CLI" if cli_active else "API Chat", inline=True)
        embed.add_field(name="Webhook Server", value="running" if wh_running else "stopped", inline=True)
        embed.add_field(name="Managed Channels", value=str(channels_ready), inline=True)
        embed.add_field(name="API Model", value=CLAUDE_MODEL, inline=True)
        await message.reply(embed=embed)

    # ------------------------------------------------------------------
    # API chat
    # ------------------------------------------------------------------

    async def _handle_api_chat(self, message, user_id, user_name, user_msg):
        logger.info(f"Chat from {user_name}: {user_msg[:100]}")

        if user_id not in self.conversation_history:
            self.conversation_history[user_id] = []

        async with message.channel.typing():
            try:
                self.conversation_history[user_id].append({"role": "user", "content": user_msg})
                if len(self.conversation_history[user_id]) > self.MAX_HISTORY:
                    self.conversation_history[user_id] = self.conversation_history[user_id][-self.MAX_HISTORY:]

                response = await asyncio.to_thread(
                    self.claude.messages.create,
                    model=CLAUDE_MODEL,
                    max_tokens=2048,
                    tools=TOOLS,
                    messages=self.conversation_history[user_id],
                    system=SYSTEM_PROMPT,
                )

                # Tool use loop
                iterations = 0
                while response.stop_reason == "tool_use" and iterations < 5:
                    iterations += 1
                    tool_blocks = [b for b in response.content if b.type == "tool_use"]
                    tool_results = []

                    for tb in tool_blocks:
                        logger.info(f"Tool call: {tb.name}")
                        result = await self._execute_tool(tb.name, tb.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tb.id,
                            "content": result,
                        })

                        # Progress update in Discord
                        preview = result[:150].replace('\n', ' ')
                        if len(result) > 150:
                            preview += "..."
                        await message.channel.send(f"\U0001f527 **{tb.name}**\n```\n{preview}\n```")

                    self.conversation_history[user_id].append({"role": "assistant", "content": response.content})
                    self.conversation_history[user_id].append({"role": "user", "content": tool_results})

                    response = await asyncio.to_thread(
                        self.claude.messages.create,
                        model=CLAUDE_MODEL,
                        max_tokens=2048,
                        tools=TOOLS,
                        messages=self.conversation_history[user_id],
                    )

                # Extract final text
                final_text = "".join(b.text for b in response.content if hasattr(b, 'text'))

                if final_text:
                    self.conversation_history[user_id].append({"role": "assistant", "content": final_text})
                    # Split long messages
                    if len(final_text) > 1900:
                        pages = [final_text[i:i + 1900] for i in range(0, len(final_text), 1900)]
                        for i, page in enumerate(pages):
                            suffix = f" ({i + 1}/{len(pages)})" if len(pages) > 1 else ""
                            await message.channel.send(f"{page}{suffix}")
                    else:
                        await message.channel.send(final_text)
                else:
                    await message.channel.send("No response generated.")

            except anthropic.APIError as e:
                logger.error(f"Claude API error: {e}")
                await message.channel.send(f"\u274c Claude API Error: {e}")
            except Exception as e:
                logger.error(f"Chat error: {e}", exc_info=True)
                await message.channel.send(f"\u274c Error: {e}")

    async def _execute_tool(self, name: str, inputs: dict) -> str:
        """Dispatch a tool call to the appropriate implementation."""
        if name == "read_file":
            return await asyncio.to_thread(_read_file, inputs["file_path"], inputs.get("lines"))
        elif name == "list_directory":
            return await asyncio.to_thread(_list_directory, inputs["directory_path"])
        elif name == "run_command":
            return await asyncio.to_thread(_run_command, inputs["command"])
        elif name == "get_system_info":
            return await asyncio.to_thread(_get_system_info)
        elif name == "search_logs":
            return await asyncio.to_thread(
                _search_logs, inputs["file_path"], inputs["search_term"], inputs.get("context_lines", 2),
            )
        elif name == "check_service_status":
            return await _check_service_status(self.http_session, inputs["service"])
        elif name == "get_download_queue":
            return await _get_download_queue(self.http_session, inputs["service"])
        elif name == "retry_download":
            return await _retry_download(self.http_session, inputs["service"], inputs["media_id"])
        else:
            return f"Unknown tool: {name}"

    # ------------------------------------------------------------------
    # Run
    # ------------------------------------------------------------------

    def run(self):
        self.bot.run(BOT_TOKEN)


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    logger.info("Starting Media Bot...")
    bot = MediaBot()
    bot.run()
