# scambot
A Telegram bot to track scamming activity

To run the bot yourself, you will need: 
- Python (tested with 3.4)
- The [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) module (tested with 4.2.0)
- The [Pony ORM](https://ponyorm.com/) module (tested with 0.6.4)

Get a bot token from [@BotFather](http://telegram.me/BotFather), place it in `credentials.py`. If you want to use [botan.io](http://botan.io/) for bot analyis, get a token from [@Botaniobot](http://telegram.me/Botaniobot) and also place it in `credentials.py`.

By default, the bot uses `getUpdates` to receive updates. To use a webhook, edit `start_bot.py` accordingly. Check [python-telegram-bot documentation](http://pythonhosted.org/python-telegram-bot/telegram.ext.updater.html#telegram.ext.updater.Updater.start_webhook) on more information.

Run the bot with `python3 bot.py`
