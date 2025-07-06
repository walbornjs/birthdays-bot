# Birthday notification bot

Telegram Bot to send birthday notifications.

This Bot uses the Application class to handle the bot and the JobQueue to send
timed messages.

First, a few handler functions are defined. Then, those functions are passed to
the Application and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.

Usage:
Basic Birthday Bot example, sends a messages after a set time.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.

Note:
To use the JobQueue, you must install PTB via
`pip install "python-telegram-bot[job-queue]"`

# Local development

## Create virtual environment
python3 -m venv venv && source venv/bin/activate

## Istall requirements
pip install -r requirements.txt

## Run bot
python index.py

# License
This program is dedicated to the public domain under the CC0 license.

