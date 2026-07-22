# Mini World MW Bot

Discord bot for Mini World: CREATA — kick, ban, fans, medal, points, rename, season pass.

## Features
- `!kick` — Kick player from room
- `!ban` — Ban device (force logout)
- `!unban` — Unban player
- `!banlist` — List banned players
- `!fans` — Get fan count
- `!medal` — Get medal badge
- `!points` — Get mini points
- `!rename` — Change account name
- `!season` — Get season pass data
- `!mwstatus` — Check MW API status
- `!help` — List all commands

## Setup
1. Clone repo
2. Copy `.env.example` to `.env` and fill in tokens
3. Install dependencies: `pip install -r requirements.txt`
4. Run: `python main.py`

## Environment Variables
```
DISCORD_TOKEN=your_discord_token
GUILD_ID=your_server_id
MINI_UIN=your_miniworld_uid
MINI_PW=your_miniworld_password
```

## Deploy
- **Railway**: Auto deploy from this repo
- **Docker**: `docker build -t mw-bot . && docker run mw-bot`

## Notes
- Owner DM access: user ID `1286240448775720962`
- All commands show ban risk warning before execution
- API endpoints may be rate-limited by Cloudflare Workers
