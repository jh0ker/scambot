import logging

from telegram import Updater, ParseMode, Message, Chat
from telegram.utils.botan import Botan

from credentials import TOKEN, BOTAN_TOKEN
from start_bot import start_bot

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG)
logger = logging.getLogger(__name__)

u = Updater(TOKEN)
dp = u.dispatcher

botan = False
if BOTAN_TOKEN:
    botan = Botan(BOTAN_TOKEN)

help_text = ""


def error(bot, update, error):
    """ Simple error handler """
    logger.exception(error)


def help(bot, update):
    """ Handler for the /help command """
    bot.sendMessage(update.message.chat_id,
                    text=help_text,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True)


# Add all handlers to the dispatcher and run the bot
dp.addTelegramCommandHandler('start', help)
dp.addTelegramCommandHandler('help', help)
dp.addErrorHandler(error)

start_bot(u)
u.idle()
