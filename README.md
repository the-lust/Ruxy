# Ruxy — Discord Bot for the Rux Programming Language

A feature-rich Discord bot built with **discord.py** that provides GitHub repository management, moderation, fun interactions, user information, and commit watching for the Rux ecosystem.

## Features

### GitHub Integration
- **`/repo`** — View repository info (stars, forks, language, license, topics, size, last push) with branch switching selector
- **`/contributors`** — List top contributors per repository with commit counts
- **`/releases`** — View recent releases with tags, dates, and changelogs
- **`/issues`** — Browse open/closed/all issues for any repository
- **`/pulls`** — Browse open/closed/all pull requests with merge status
- **`/docs`** — Quick links to Rux documentation, GitHub, and language home
- **`/packages`** — List all 14 repositories in the Rux ecosystem

### Commit Watcher (Log Channels)
- **`/set-log <repo> [branch]`** — Watch a repository for new commits (posts diff embeds to the channel)
- **`/remove-log`** — Stop watching in the current channel
- **`/list-logs`** — Show all active watched repositories
- Background loop checks every 120 seconds for new commits
- Embeds show: commit message, author, stats (+/-/~), changed files in diff format, raw JSON payload
- Color-coded: green for more additions, red for more deletions, purple for balanced

### Utility
- **`/ping`** — Check gateway latency
- **`/about`** — Bot version, server count, latency, library info
- **`/help`** — List all commands organized by category
- **`/stats`** — Command usage statistics (top 10 commands)
- **`/changelog`** — Version history and what's new

### User Information
- **`/userinfo [user]`** — Profile card with username, nickname, ID, creation/join dates, roles, badges (HypeSquad, Early Supporter, Active Dev, etc.)
- **`/serverinfo`** — Server overview: owner, member count (humans/bots), channels, roles, boost level
- **`/avatar [user]`** — Full-size user avatar with open link button

### Fun
- **`/rps`** — Rock Paper Scissors with interactive buttons (Rock/Paper/Scissors)
- **`/roast <member>`** — Random roast targeted at a member
- **`/rr`** — Russian Roulette with a 1-in-6 chamber, button pull
- **`/say <text>`** — Make the bot speak (max 1900 chars)

### AFK System
- **`/afk [reason]`** — Set yourself as away from keyboard
- Auto-removes AFK when you send a message, showing how long you were away
- When someone mentions an AFK user, shows their AFK duration and reason
- Duration format: years, months, weeks, days, hours, minutes, seconds

### Moderation
- **`/blacklist <user> [reason] [duration]`** — Blacklist a user from using the bot (temporary or permanent)
- **`/unblacklist <user>`** — Remove a user's blacklist
- **`/whitelist <user>`** — Manual unblacklist override

### Owner Commands
- **`/shutdown`** — Gracefully shut down the bot
- **`/restart`** — Restart the bot process
- **`/sync`** — Force sync all slash commands to Discord
- **`/reload`** — Hot-reload all cogs without restarting
- **`/diagnostics`** — Show uptime, latency, server count, Python version, platform, sync version

### Anti-Spam System
- 3 commands in 5 seconds triggers anti-spam
- 1st offense: 10-minute temp blacklist
- 2nd offense: 60-minute temp blacklist
- 3rd+ offense: permanent blacklist
- All offenses persist in SQLite across restarts

### Components V2 UI
- All messages use **discord.py Components V2** (`LayoutView`, `Container`, `TextDisplay`)
- Interactive select menus for branch switching in `/repo`
- Button rows for navigation and external links
- Color-coded accents: green (success), red (error/danger), purple (default), yellow (warning)

### Logging & Metrics
- Rotating file logs: `bot.log` (INFO+), `errors.log` (ERROR+), `github.log` (GitHub API calls)
- Command usage tracking in SQLite for `/stats`
- Cooldowns on all commands to prevent abuse

## Configuration

Copy `.env.example` to `.env` and fill in:

```env
DISCORD_TOKEN=your_bot_token_here
OWNER_IDS=123456789012345678,987654321098765432
```

| Variable | Description |
|---|---|
| `DISCORD_TOKEN` | Discord bot token (required) |
| `OWNER_IDS` | Comma-separated user IDs with owner access |

### config.py constants

| Setting | Default | Description |
|---|---|---|
| `BOT_COLOR` | `#A259FF` | Primary embed/accent color |
| `BOT_NAME` | `Ruxy` | Bot display name |
| `BOT_VERSION` | `4.1.0` | Current version |
| `GITHUB_ORG` | `rux-lang` | GitHub organization |
| `GITHUB_TIMEOUT` | `10` | API request timeout (seconds) |
| `CACHE_TTL` | `120` | API cache TTL (seconds) |

## Installation

```bash
pip install -r requirements.txt
```

**Requirements:** Python 3.10+, discord.py >=2.4.0, aiohttp >=3.9.0, python-dotenv >=1.0.0

## Commands

All commands use slash (`/`) notation:

### Utility
`/ping` `/about` `/help` `/stats` `/changelog`

### GitHub
`/repo` `/contributors` `/releases` `/issues` `/pulls` `/docs` `/packages`

### Fun
`/rps` `/roast` `/rr` `/say` `/afk`

### User Info
`/userinfo` `/serverinfo` `/avatar`

### Moderation
`/blacklist` `/unblacklist` `/whitelist`

### Owner
`/shutdown` `/restart` `/sync` `/reload` `/diagnostics`

### Log Channels
`/set-log` `/remove-log` `/list-logs`

## Database

Uses SQLite (`ruxy.db`) with the following tables:

| Table | Purpose |
|---|---|
| `blacklist` | User blacklist with expiry and permanence |
| `spam_state` | Anti-spam tracking for cooldown enforcement |
| `sync_state` | Stored command sync version for auto-sync |
| `command_metrics` | Usage logging for `/stats` |
| `settings` | Per-guild key-value settings |
| `log_channels` | GitHub commit watch channels |
| `afk_users` | AFK status with timestamps |

## Project Structure

```
Ruxy-v4/
├── bot.py                 # Entry point, client setup, cog loading
├── config.py              # Constants and environment loading
├── cogs/
│   ├── afk.py             # AFK command + on_message listener
│   ├── fun.py             # RPS, roast, Russian Roulette, say
│   ├── github.py          # All GitHub commands + CV2 view builders
│   ├── logs.py            # Log channel management (commit watcher)
│   ├── moderation.py      # Blacklist/unblacklist/whitelist
│   ├── owner.py           # Owner-only commands
│   ├── userinfo.py        # User/server info + avatar
│   └── utility.py         # Ping, about, help, stats, changelog
├── services/
│   ├── cache.py           # TTL cache for GitHub API
│   ├── commit_watcher.py  # Commit/PR embed builders
│   ├── cv2.py             # Components V2 view builders
│   ├── embeds.py          # Legacy embed builders (used by logs cog)
│   ├── github_api.py      # Async GitHub API client
│   └── logger.py          # Logging configuration
├── database/
│   └── db.py              # SQLite database layer
├── utils/
│   ├── checks.py          # Blacklist, jail, anti-spam checks
│   └── permissions.py     # Owner/mod/admin role checks
├── logs/                  # Rotating log files
├── .env                   # Environment variables (gitignored)
└── requirements.txt       # Python dependencies
```
