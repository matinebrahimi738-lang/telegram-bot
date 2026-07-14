# PLM - Penalty League Mobin (Telegram Bot)

Professional bilingual Telegram bot for penalty competitions, built with **Python + aiogram 3.x + SQLite**.

## Features

- Bilingual bot: **Persian / English**
- First-entry language selection + language change from menu
- All bot texts loaded from locale files:
  - `telegram_bot/locales/fa.json`
  - `telegram_bot/locales/en.json`
- Modern inline keyboard-driven UX
- User menu:
  - Join Competition
  - Guide
  - Rules
  - Leaderboard
  - Change Language
  - Support
- Admin panel (`/admin`):
  - Create Match (3 or 5 rounds)
  - Active Matches
  - Manage Players
  - Stats
  - Leaderboard
  - Broadcast
  - Settings
  - Delete Match
- Player registration:
  - Name
  - Telegram username
  - Country
  - Duplicate registration prevention
- Match engine:
  - 3-direction system: Left / Center / Right
  - Role swap each round (Shooter/Goalkeeper)
  - One direction submit per player per round
  - Admin round decision: Goal / Save / Out
- Automatic persistence:
  - Round results
  - Match final result
  - Player statistics
  - Leaderboard
- Broadcast targeting:
  - Persian users
  - English users
  - All users
- Security and reliability:
  - Admin-only management panel
  - Anti-spam middleware
  - Input validation
  - Logging + global error handling
- Modular and production-ready structure

---

## Tech Stack

- Python 3.10+
- aiogram 3.x
- SQLite (aiosqlite)
- Async / FSM / OOP / Type hints

---

## Project Structure

```bash
telegram_bot/
  config.py
  main.py
  database/
    db.py
  filters/
    is_admin.py
  handlers/
    start.py
    user.py
    admin.py
    errors.py
  keyboards/
    inline.py
  locales/
    en.json
    fa.json
  middlewares/
    spam.py
  services/
    match_service.py
  states/
    forms.py
  utils/
    i18n.py
    logger.py
    validators.py
  data/
  logs/
```

---

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Create environment file:

```bash
cp .env.example .env
```

3. Fill required values in `.env`:

- `BOT_TOKEN`
- `ADMIN_ID`

4. Run bot:

```bash
python -m telegram_bot.main
```

---

## Render Deployment

Use a **Background Worker** service:

- Build Command:

```bash
pip install -r requirements.txt
```

- Start Command:

```bash
python -m telegram_bot.main
```

- Environment Variables:
  - `BOT_TOKEN`
  - `ADMIN_ID`
  - `SUPPORT_USERNAME`
  - `SQLITE_PATH` (optional)
  - `LOG_LEVEL` (optional)

> Note: SQLite is local file-based. For persistent production usage, attach a persistent disk on Render.

---

## VPS Deployment (systemd sample)

Create service file `/etc/systemd/system/plm-bot.service`:

```ini
[Unit]
Description=PLM Telegram Bot
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/path/to/project
Environment="BOT_TOKEN=..."
Environment="ADMIN_ID=..."
Environment="SUPPORT_USERNAME=@support"
ExecStart=/usr/bin/python3 -m telegram_bot.main
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable plm-bot
sudo systemctl start plm-bot
sudo systemctl status plm-bot
```

---

## Notes

- All UI texts are locale-driven.
- Admin result is required to finalize each round.
- Leaderboard is generated from persisted player statistics.
- Logs are written to `telegram_bot/logs/bot.log`.
