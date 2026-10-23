# GoldPulse Bot

A Telegram bot that retrieves the current global gold spot price (XAU) and
delivers it to subscribed users every two minutes.

**English-only project.** All documentation, code comments, log messages, and
user-facing text are in English.

## What GoldPulse Bot does

- Fetches the live XAU (gold) spot price from the public
  [api.gold-api.com](https://api.gold-api.com/price/XAU) endpoint.
- Sends a scheduled price update to every subscribed Telegram user every
  120 seconds (2 minutes).
- Lets users subscribe with `/start` and unsubscribe with `/stop`.
- Offers `/price` to fetch the latest price on demand and `/help` for usage.
- Persists subscriber chat IDs in a local SQLite database, so subscriptions
  survive restarts.
- Never sends a fabricated or stale price. If the price API fails, the update
  is skipped and the error is logged in English.
- Only sends scheduled notifications to users who have subscribed via `/start`.

## Prerequisites

- Windows 10 / 11
- Python 3.11 or newer (this project was developed with Python 3.13)
- A Telegram account and a bot token from [BotFather](https://t.me/botfather)
- Internet access to reach the gold-price API and Telegram

No paid API or paid service is required for the core implementation.

## Setup on Windows using Git CMD

Open **Git CMD** (or Git Bash) and run the commands below.

### 1. Clone or create the project folder

```cmd
cd D:\Projects
mkdir Goldpulse-Telegram-Bot
cd Goldpulse-Telegram-Bot
```

Place the project files in this folder, or clone the repository once it is
published.

### 2. Create and activate a Python virtual environment

```cmd
python -m venv .venv
.venv\Scripts\activate
```

You should see `(.venv)` prefixed in your prompt. To deactivate later:

```cmd
deactivate
```

### 3. Install dependencies

```cmd
pip install --upgrade pip
pip install -r requirements.txt
```

> Note: if your configured PyPI mirror has certificate issues, install from the
> official index: `pip install --index-url https://pypi.org/simple -r requirements.txt`

### 4. Create a Telegram bot with BotFather

1. Open Telegram and message [@BotFather](https://t.me/botfather).
2. Send `/newbot` and follow the prompts to choose a name and username.
3. BotFather will reply with a bot token (for example:
   `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`).
4. **Keep the token secret.** Do not share it, commit it, or paste it in chat.

### 5. Configure `.env` securely

Copy the example file and fill in your token:

```cmd
copy .env.example .env
notepad .env
```

Edit `.env` so it contains your real token:

```
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
```

Save and close the file. The `.env` file is listed in `.gitignore` and must
never be committed.

### 6. Initialize and run the bot

```cmd
python -m goldpulse_bot
```

or

```cmd
python main.py
```

The bot starts polling Telegram and begins scheduling gold-price updates every
2 minutes. You will see log output in English. Press `Ctrl+C` to stop the bot.

> The bot only runs while the Python process is running. Stopping the terminal
> or the process stops the bot.

## Bot commands

| Command | Description |
|---------|-------------|
| `/start` | Subscribe to gold price updates every 2 minutes and receive the current price. Idempotent: repeating `/start` does not create duplicate subscriptions. |
| `/stop` | Unsubscribe from automatic price updates. Idempotent: repeating `/stop` when already unsubscribed is harmless. |
| `/price` | Request the latest available price immediately. |
| `/help` | Show a concise description of the bot and all commands. |

## Running automated tests

```cmd
pytest
```

Tests mock the external gold-price API and Telegram interactions, so no real
bot token and no network calls are required. All tests must pass before
committing.

## Stopping and restarting the application

- Stop: press `Ctrl+C` in the terminal where the bot runs.
- Restart: run `python -m goldpulse_bot` again. Subscriptions are preserved in
  the SQLite database, so users do not need to re-subscribe.

## Keeping the bot running when a terminal session closes (Windows)

Because the bot is a normal Python process, closing the terminal stops it. For
long-running operation on Windows, use one of these safe, appropriate options:

### Option A: Windows Task Scheduler (recommended for personal use)

1. Open Task Scheduler and create a **Basic Task**.
2. Set the trigger to "When I log on" or daily at a chosen time.
3. Set the action to "Start a program":
   - Program/script: `C:\Users\RTS\AppData\Local\Programs\Python\Python313\python.exe`
   - Add arguments: `-m goldpulse_bot`
   - Start in: `D:\Projects\Goldpulse-Telegram-Bot`
4. Finish and enable the task.

Adjust the Python path and project folder to match your installation.

### Option B: Run as a background process with `pythonw.exe`

To avoid a console window:

```cmd
start /b pythonw -m goldpulse_bot
```

### Option C: Third-party Windows service wrappers

Tools such as [NSSM](https://nssm.cc/) (Non-Sucking Service Manager) can install
the bot as a Windows service so it starts automatically and survives logoff.

> Do not rely on keeping a terminal window open. Use Task Scheduler, NSSM, or a
> similar mechanism for unattended, continuous operation.

## Limitations of the public gold-price API

- The public `api.gold-api.com/price/XAU` endpoint is free but not guaranteed
  to be available 24/7 or to meet a commercial SLA.
- Price freshness depends on the API's `updatedAt` timestamp, which the bot
  displays only when the API supplies a trustworthy value.
- The bot does not fabricate prices. During API outages, scheduled updates are
  skipped and errors are logged.
- For production or financial use, subscribe to a paid, reliable market-data
  provider.

## Project structure

```
goldpulse-bot/
├── .env.example            # Placeholder configuration (copy to .env)
├── .gitignore              # Git ignore rules
├── main.py                 # Script entry point
├── pyproject.toml          # Project metadata and pytest config
├── requirements.txt        # Python dependencies
├── README.md               # This file
├── goldpulse_bot/
│   ├── __init__.py         # Package marker
│   ├── __main__.py         # `python -m goldpulse_bot` entry
│   ├── api_client.py       # Gold price API client (httpx)
│   ├── bot.py              # Bot initialization and job scheduling
│   ├── config.py           # Settings from environment / .env
│   ├── database.py         # SQLite subscriber persistence
│   ├── handlers.py         # Telegram command handlers (/start /stop /price /help)
│   ├── logging_config.py   # Logging configuration
│   └── scheduler.py        # Scheduled price-update logic
└── tests/
    ├── conftest.py         # Pytest fixtures
    ├── test_api_client.py  # API client tests
    ├── test_config.py      # Configuration tests
    ├── test_database.py    # Subscriber persistence tests
    ├── test_handlers.py    # Command handler tests
    └── test_scheduler.py   # Scheduled-update tests
```

## Security

- The Telegram bot token is read only from the `TELEGRAM_BOT_TOKEN`
  environment variable (`.env` for local development).
- `.env`, `*.sqlite`, `*.db`, virtual environments, logs, and caches are in
  `.gitignore` and are not committed.
- No real token, secret, or generated file is stored in source control.
- Logs never print secrets.

## License

This project is provided as-is for educational and personal use.
