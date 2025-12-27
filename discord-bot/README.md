# Discord Claude Bot - Media Server Integration

Your Discord Claude Bot is now running and ready to use!

## Quick Start

### Bot Status
- **Container**: `discord-claude-bot` (running)
- **Bot Name**: Media-Server-Bot
- **Bot ID**: 1454472436752846869
- **Status**: ✅ Connected to Discord

### Testing the Bot

Go to your Discord server's `#media-logs` channel and send a message starting with `Claude`:

```
Claude What errors are in the media server logs?
```

The bot will:
1. Analyze your request
2. Use its tools to fetch logs and system info
3. Use Claude AI to analyze the results
4. Return an intelligent response

### Available Commands

Test these commands in Discord to see the bot in action:

#### 1. System Health Check
```
Claude Is the server running healthy? Check disk, memory, and CPU.
```
Claude will fetch system information and provide a health summary.

#### 2. Check Specific Logs
```
Claude What errors are in the Sonarr logs from the last hour?
```
Claude will read the Sonarr logs and analyze them for errors.

#### 3. Service Status
```
Claude Which Docker services are running? Are there any unhealthy containers?
```
Claude will list running services and their status.

#### 4. Search Logs for Specific Terms
```
Claude Search for "ERROR" in the SABnzbd logs and explain what happened.
```
Claude will find relevant log entries and provide context.

#### 5. Disk Space Analysis
```
Claude Where is disk space being used? What's taking up the most space?
```
Claude will analyze disk usage and identify large directories.

### Available Tools

The bot has access to these tools:

- **read_file**: Read log files and configuration files
- **list_directory**: Browse directories on the server
- **run_command**: Execute read-only diagnostic commands (ps, df, docker, etc.)
- **get_system_info**: Get CPU, memory, disk, and uptime information
- **search_logs**: Search for text patterns in log files

### Security Features

- ✅ Command whitelist (only safe, read-only commands allowed)
- ✅ Path restrictions (can't access /root, /var/lib, etc.)
- ✅ User permissions (optional, set ALLOWED_USERS in .env)
- ✅ Audit logging (all actions logged to `/opt/mediaserver/discord-bot/logs/bot.log`)
- ✅ Output truncation (responses limited to 2000 chars to fit Discord)

### Monitoring the Bot

#### View Live Logs
```bash
docker compose logs -f discord-bot
```

#### Check Bot Health
```bash
docker compose ps discord-bot
```

#### View Bot's Audit Log
```bash
tail -f /opt/mediaserver/discord-bot/logs/bot.log
```

### Conversation History

The bot maintains conversation history per user (up to 20 messages). This allows Claude to:
- Remember context from previous questions
- Refer back to earlier information
- Provide more accurate follow-up responses

Reset conversation by having the user ask a different question (history is per-user, so different users have separate conversations).

### API Costs

Each message you send uses Claude's API and costs:
- **Input**: ~$0.003 per 1K tokens (typically 100-500 tokens per message)
- **Output**: ~$0.015 per 1K tokens (typically 200-1000 tokens per response)

**Example costs**:
- Simple system check: ~$0.01-0.02
- Log analysis with multiple files: ~$0.05-0.15
- Complex troubleshooting: ~$0.10-0.30

**Budget Recommendation**: With typical usage (5-10 queries/day), expect ~$5-10/month.

### Troubleshooting

#### Bot Not Responding
1. Check bot is in the #media-logs channel
2. Verify message starts with `Claude ` (with space)
3. Check logs: `docker compose logs discord-bot --tail=50`

#### "Claude API Error"
1. Check your API key is valid in the `.env` file
2. Verify you have API credits in your Anthropic account
3. Check rate limits haven't been exceeded

#### "Command not allowed"
- Only read-only commands are permitted
- The whitelist is in `bot.py` (allowed_prefixes)
- Contact the admin to expand allowed commands

#### "Access denied" on files
- File path must be in the allowed list: `/var/log`, `/opt`, `/mnt`, `/home`, `/etc`, `/var/spool/cron`
- Contact the admin to expand file access

### Configuration

**File**: `/opt/mediaserver/.env`

Key settings:
```bash
DISCORD_BOT_TOKEN=<your-bot-token>
ANTHROPIC_API_KEY=<your-api-key>
ALLOWED_USERS=  # Leave empty for all users, or add user#discriminator
```

**File**: `/opt/mediaserver/discord-bot/bot.py`

Customization options:
- `MAX_HISTORY_PER_USER`: Increase for longer conversations (default: 20 messages)
- `allowed_prefixes`: Add more commands to whitelist
- `allowed_dirs`: Expand file access restrictions
- Tool implementations: Add new tools or modify existing ones

### Advanced: Adding Custom Tools

Want to add a new tool? Edit `bot.py` and:

1. Add tool definition to `TOOLS` list
2. Implement the tool function
3. Add case in `process_tool_call()`
4. Restart: `docker compose restart discord-bot`

Example:
```python
{
    "name": "check_plex_status",
    "description": "Check if Plex server is responding",
    "input_schema": {...}
}

def check_plex_status() -> str:
    # Implementation here
    pass
```

### Support

- **Docker logs**: `docker compose logs discord-bot`
- **Bot logs**: `/opt/mediaserver/discord-bot/logs/bot.log`
- **Error messages**: Check Discord's response or bot logs for details
- **Questions**: Reference the full guide at `/opt/mediaserver/docs/Discord Bot with Claude API.md`

---

**Last Updated**: 2025-12-27
**Bot Status**: ✅ Running and Ready
