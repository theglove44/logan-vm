# Discord Bot with Claude Code CLI Integration

This bot runs the actual `claude` CLI from `/opt/mediaserver` and forwards all interactions to Discord.

## Key Differences from API Bot

| Feature | API Bot (bot.py) | Claude Code Bot (bot-claude-code.py) |
|---------|------------------|--------------------------------------|
| **Backend** | Claude API with custom tools | Full Claude Code CLI |
| **Capabilities** | Limited to predefined tools | All Claude Code features (Read, Edit, Write, Bash, etc.) |
| **Context** | Limited conversation history | Full Claude Code context management |
| **Approvals** | Auto-approved | Forwarded to Discord for user approval |
| **Session** | Stateless (new each time) | Persistent session per channel |
| **Working Dir** | N/A | Runs from /opt/mediaserver |

## How It Works

1. **Persistent Sessions**: Each Discord channel gets its own Claude Code session that persists
2. **Full Access**: Claude Code has access to all its normal tools (Read, Write, Edit, Bash, etc.)
3. **Interactive Approvals**: When Claude Code needs approval (like running commands), it sends a message to Discord with ✅/❌ reactions
4. **Context Awareness**: The bot includes a system prompt with media server log locations and architecture

## Installation

### 1. Install pexpect

```bash
cd /opt/mediaserver/discord-bot
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Test Run (Manual)

```bash
./run-claude-code-bot.sh
```

You should see:
```
Starting Discord Claude Code bot...
Working directory: /opt/mediaserver
Claude CLI path: /home/christof21/.npm-global/bin/claude

✅ Bot logged in as Media-Server-Bot
✅ Bot ID: <your-bot-id>
✅ Working directory: /opt/mediaserver
✅ Claude Code Bot is ready!
```

### 3. Test in Discord

Go to your `#media-logs` channel and try:

```
Claude status
```

You should see: `✅ Claude Code session is running`

Then try a real query:

```
Claude check the Sonarr logs for any errors in the last 100 lines
```

Claude Code will:
1. Use the Read tool to open the log file
2. **Ask for approval** (you'll see a message with ✅/❌ reactions)
3. Click ✅ to approve
4. Show you the results

## Usage Examples

### Basic Queries

```
Claude what's the disk usage on the server?
```

```
Claude show me the last 50 lines of the Radarr logs
```

```
Claude are there any unhealthy Docker containers?
```

### Advanced Operations

```
Claude search all media server logs for "error" and summarize what you find
```

```
Claude compare the Sonarr and Radarr configurations and tell me if they're consistent
```

### Approval Workflow

When Claude Code wants to run a command or read a file, you'll see:

```
🔧 Claude Code is requesting permission:

Read file: /opt/mediaserver/sonarr/logs/sonarr.txt

Allow? (y/n):
```

Click:
- ✅ to approve (sends 'y')
- ❌ to deny (sends 'n')

### Special Commands

```
Claude restart
```
Restarts the Claude Code session for this channel (clears context)

```
Claude status
```
Shows if Claude Code session is running

## Production Deployment (systemd)

Create `/etc/systemd/system/discord-claude-code-bot.service`:

```ini
[Unit]
Description=Discord Bot with Claude Code Integration
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=christof21
Group=christof21
WorkingDirectory=/opt/mediaserver/discord-bot
Environment="PATH=/home/christof21/.npm-global/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="PYTHONUNBUFFERED=1"
Environment="CLAUDE_WORKING_DIR=/opt/mediaserver"
ExecStart=/opt/mediaserver/discord-bot/venv-claude-code/bin/python /opt/mediaserver/discord-bot/bot-claude-code.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=discord-claude-code-bot

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable discord-claude-code-bot
sudo systemctl start discord-claude-code-bot
sudo systemctl status discord-claude-code-bot
```

View logs:

```bash
journalctl -u discord-claude-code-bot -f
```

Or check bot logs:

```bash
tail -f /opt/mediaserver/discord-bot/logs/bot-claude-code.log
```

## Troubleshooting

### Bot not responding

1. Check if Claude CLI is accessible:
```bash
which claude
claude --version
```

2. Check bot logs:
```bash
tail -50 /opt/mediaserver/discord-bot/logs/bot-claude-code.log
```

3. Restart the bot:
```bash
Claude restart
```

### Claude Code session stuck

If the bot stops responding, restart the session:

```
Claude restart
```

This will kill the old Claude Code process and start fresh.

### Approval prompts not working

Make sure the bot has permission to:
- Add reactions to messages
- Read message reactions

Check Discord bot permissions in your server settings.

### Process not found errors

Make sure PATH includes Claude CLI:

```bash
export PATH="/home/christof21/.npm-global/bin:$PATH"
```

## Architecture

```
┌─────────────────────────────────┐
│   Discord #media-logs Channel   │
│   User: "Claude check logs"     │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│    Discord Bot (Python)         │
│  - Manages Discord connection   │
│  - Spawns Claude Code process   │
│  - Forwards messages            │
│  - Handles approval prompts     │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│  Claude Code CLI (pexpect)      │
│  Working Dir: /opt/mediaserver  │
│  - Read/Write/Edit tools        │
│  - Bash command execution       │
│  - Full context awareness       │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│   /opt/mediaserver filesystem   │
│   - Service configs             │
│   - Log files                   │
│   - Docker Compose files        │
└─────────────────────────────────┘
```

## Security Considerations

1. **Approvals**: Always review what Claude Code wants to do before clicking ✅
2. **Commands**: Claude Code can run any command - be careful with destructive operations
3. **File Access**: Claude Code can read/write files in /opt/mediaserver
4. **User Control**: Set `ALLOWED_USERS` in `.env` to restrict who can use the bot
5. **Session Isolation**: Each Discord channel has its own Claude Code session

## Tips

- Be specific in your requests: "Check last 100 lines of Sonarr logs" is better than "check logs"
- Use `Claude restart` if the session seems confused or stuck
- Approve read-only operations (logs, status checks) freely
- Review write operations (edits, config changes) carefully
- The bot remembers context within a channel, so you can have conversations

## Comparison: When to Use Which Bot

### Use API Bot (bot.py) when:
- You want faster responses (no approval prompts)
- You only need predefined operations (check logs, system status)
- You want auto-approved actions
- You need lower costs (fewer API calls)

### Use Claude Code Bot (bot-claude-code.py) when:
- You need full Claude Code capabilities
- You want to make config changes or edits
- You need complex multi-step operations
- You want explicit approval control
- You need rich context awareness

## Next Steps

1. Test the bot in Discord with simple queries
2. Try operations that need approval (reading files, running commands)
3. Set up systemd service for production
4. Configure ALLOWED_USERS in .env for security
5. Monitor logs to ensure everything works smoothly

## Cost Considerations

Claude Code uses the Claude API on the backend. Costs depend on:
- Token usage (input + output)
- Model used (defaults to Sonnet 4.5)
- Conversation length

Typical costs:
- Simple log check: $0.01-0.05
- Complex multi-file analysis: $0.10-0.50
- Long conversation: $0.50-2.00

Monitor usage in Anthropic Console.
