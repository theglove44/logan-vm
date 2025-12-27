# Discord Claude Bot - Quick Reference

## How to Use

Send a message in Discord starting with `Claude `:

```
Claude <your question>
```

## Example Queries

### Diagnostics
```
Claude What's the system health? Check disk, memory, and CPU.
Claude Are there any errors in the logs?
Claude Which services are failing?
```

### Log Analysis
```
Claude What happened in the Sonarr logs in the last hour?
Claude Search for "ERROR" in all media server logs
Claude Why is SABnzbd having issues?
```

### File Management
```
Claude What files are in the downloads folder?
Claude How much disk space is each service using?
Claude Find large files on the server
```

### General Troubleshooting
```
Claude Help me troubleshoot the media server
Claude Why can't Sonarr find downloads?
Claude Is there a network connectivity issue?
```

## Command Syntax

- **Start with**: `Claude ` (capital C, space after)
- **Questions**: Natural language, Claude will understand
- **Context**: Claude remembers previous questions in conversation
- **Response**: Sent to Discord as code block (auto-formatted)

## Tools Claude Can Use

Claude automatically chooses which tools to use based on your question:

- **read_file** - Read logs and configs
- **list_directory** - Browse folders
- **run_command** - Execute diagnostics
- **get_system_info** - System stats
- **search_logs** - Find text in logs

## Response Format

Responses appear in Discord as:

```
[Claude's analysis and findings]
```

Long responses are automatically split across multiple messages.

## If Something Goes Wrong

**Bot not responding?**
- Ensure message starts with `Claude ` (capital C)
- Check bot is in the channel

**Got an error?**
- Check bot logs: `docker compose logs discord-bot`
- Verify `.env` file has correct tokens

**Rate limited?**
- Wait a few minutes
- Check Anthropic API quota
- Monitor costs in Anthropic console

## File Locations

- **Bot code**: `/opt/mediaserver/discord-bot/bot.py`
- **Configuration**: `/opt/mediaserver/.env`
- **Logs**: `/opt/mediaserver/discord-bot/logs/bot.log`
- **Docker**: `docker compose` in `/opt/mediaserver/`

## Container Management

```bash
# View logs
docker compose logs -f discord-bot

# Restart bot
docker compose restart discord-bot

# Stop bot
docker compose stop discord-bot

# Start bot
docker compose start discord-bot

# Check status
docker compose ps discord-bot
```

## Cost Tracking

Monitor your Claude API usage:
1. Go to https://console.anthropic.com
2. Check "Usage" tab
3. View daily/monthly spending

## Tips & Tricks

- Be specific in questions for better results
- Ask follow-up questions to get more details
- Use natural language - Claude understands context
- The bot remembers your conversation within limits

---

**Bot Status**: Running ✅
**Location**: #media-logs channel
**Help Command**: Just ask!
