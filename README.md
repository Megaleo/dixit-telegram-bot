# dixit-telegram-bot
A Telegram Bot to play Dixit with your friends!

## Requirements
- `python 3.9` or higher*
- [`python-telegram-bot`](https://pypi.org/project/python-telegram-bot/), version `13.11` or higher*, but not version 20
- [`Pillow`](https://pypi.org/project/Pillow/), version `9.0.1` or higher*
- [`pycairo`](https://pypi.org/project/pycairo/), version `1.20.1` or higher* (and its dependencies, notably [the cairo library](https://cairographics.org/))
- A bot token from telegram's [BotFather](https://telegram.me/botfather)
##### For development
- [`pytest`](https://pypi.org/project/pytest/), version `7.1.2` or higher*

*\*quite possibly lower, the minimal version is not actually known*

## Hosting
- Create a `token.txt` file, containing your bot's token, in the same directory as the `main.py` file.
- Run with `python3 main.py`
