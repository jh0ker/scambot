import logging

from telegram.ext import Updater
from telegram import ParseMode
from telegram.utils.botan import Botan
from pony.orm import db_session, select

from credentials import TOKEN, BOTAN_TOKEN
from start_bot import start_bot
from database import db

from admin import Admin
from scammer import Scammer

# States the bot can have (maintained per chat id)
MAIN, ADD_SCAMMER, REMOVE_SCAMMER, ADD_ADMIN, REMOVE_ADMIN = range(5)
state = dict()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG)
logger = logging.getLogger(__name__)

u = Updater(TOKEN)
dp = u.dispatcher

db.bind('sqlite', 'bot.sqlite', create_db=True)
db.generate_mapping(create_tables=True)

with db_session:
    if len(select(a for a in Admin if a.id is 10049375)) is 0:
        # Create initial admin account
        Admin(id=10049375, first_name="Jannes", super_admin=True)
    if len(select(a for a in Admin if a.id is 46348706)) is 0:
        # Create initial admin account
        Admin(id=46348706, first_name="Jackson", super_admin=True)
        # pass

botan = False
if BOTAN_TOKEN:
    botan = Botan(BOTAN_TOKEN)

help_text = "Check if a Telegram Account is a registered scammer.\n\n" \
            "<b>Usage:</b>\n" \
            "Forward a message of the User you want to check to this bot."

admin_help_text = "\n\n" \
                  "<b>Admin commands:</b>\n" \
                  "/add - Register a new account as a scammer\n" \
                  "/remove - Remove a registered scammer from the database\n" \
                  "/cancel - Cancel current operation"
super_admin_help_text = "\n\n" \
                        "<b>Super Admin commands:</b>\n" \
                        "/add_admin - Register a new admin\n" \
                        "/remove_admin - Remove an admin"


def error(bot, update, error):
    """ Simple error handler """
    logger.exception(error)


def help(bot, update):
    """ Handler for the /help command """
    from_user = update.message.from_user
    chat_id = update.message.chat_id

    is_admin, admin = get_admin(from_user)

    text = help_text

    if admin:
        text += admin_help_text
        if admin.super_admin:
            text += super_admin_help_text

    bot.sendMessage(chat_id,
                    text=text,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True)


@db_session
def get_admin(from_user):
    admin = list(select(a for a in Admin
                        if a.id is from_user.id))
    is_admin = bool(len(admin))
    if is_admin:
        admin[0].first_name = from_user.first_name
        admin[0].last_name = from_user.last_name
        admin[0].username = from_user.username
        admin = admin[0]
    else:
        admin = None
    return is_admin, admin


@db_session
def get_scammer(from_user):
    scammer = list(select(s for s in Scammer
                          if s.id is from_user.id))
    is_scammer = bool(len(scammer))
    if is_scammer:
        scammer[0].first_name = from_user.first_name
        scammer[0].last_name = from_user.last_name
        scammer[0].username = from_user.username
        scammer = scammer[0]
    else:
        scammer = None
    return is_scammer, scammer


def message_handler(bot, update):
    global state
    forward_from = update.message.forward_from
    chat_id = update.message.chat_id
    chat_state = state.get(chat_id, MAIN)
    if forward_from:
        if chat_state is MAIN:
            is_scammer, _ = get_scammer(forward_from)
            if is_scammer:
                reply = "This user has been registered as a scammer"
            else:
                reply = "This user has <b>not</b> been registered as a scammer"
        elif chat_state is ADD_SCAMMER:
            state[chat_id] = MAIN
            is_scammer, scammer = get_scammer(forward_from)
            if not is_scammer:
                with db_session:
                    Scammer(id=forward_from.id,
                            first_name=forward_from.first_name,
                            last_name=forward_from.last_name,
                            username=forward_from.username)
                reply = "Successfully added scammer"
            else:
                reply = "Scammer was already added"
        elif chat_state is REMOVE_SCAMMER:
            state[chat_id] = MAIN
            with db_session:
                is_scammer, scammer = get_scammer(forward_from)
                if is_scammer:
                    scammer.delete()
                    reply = "Successfully removed scammer"
                else:
                    reply = "This user is not a registered scammer"
        elif chat_state is ADD_ADMIN:
            state[chat_id] = MAIN
            is_admin, admin = get_admin(forward_from)
            if not is_admin:
                with db_session:
                    Admin(id=forward_from.id,
                          first_name=forward_from.first_name,
                          last_name=forward_from.last_name,
                          username=forward_from.username)
                reply = "Successfully added admin"
            else:
                reply = "This user is already an admin"
        elif chat_state is REMOVE_ADMIN:
            state[chat_id] = MAIN
            with db_session:
                is_admin, admin = get_admin(forward_from)
                if is_admin and not admin.super_admin:
                    admin.delete()
                    reply = "Successfully removed admin"
                else:
                    reply = "This user is not an admin"

        bot.sendMessage(chat_id, text=reply, parse_mode=ParseMode.HTML,
                        reply_to_message_id=update.message.message_id)


def add_scammer(bot, update):
    global state
    is_admin, _ = get_admin(update.message.from_user)
    if not is_admin:
        return
    state[update.message.chat_id] = ADD_SCAMMER
    bot.sendMessage(update.message.chat_id,
                    text="Forward me a message of the scammer you want to add"
                         " or send /cancel to cancel")


def remove_scammer(bot, update):
    global state
    is_admin, _ = get_admin(update.message.from_user)
    if not is_admin:
        return
    state[update.message.chat_id] = REMOVE_SCAMMER
    bot.sendMessage(update.message.chat_id,
                    text="Forward me a message of the user you want to remove"
                         " or send /cancel to cancel")


def add_admin(bot, update):
    global state
    is_admin, admin = get_admin(update.message.from_user)
    if not is_admin or not admin.super_admin:
        return
    state[update.message.chat_id] = ADD_ADMIN
    bot.sendMessage(update.message.chat_id,
                    text="Forward me a message of the user you want to add"
                         " as admin or send /cancel to cancel")


def remove_admin(bot, update):
    global state
    is_admin, admin = get_admin(update.message.from_user)
    if not is_admin or not admin.super_admin:
        return
    state[update.message.chat_id] = REMOVE_ADMIN
    bot.sendMessage(update.message.chat_id,
                    text="Forward me a message of the admin you want to remove"
                         " or send /cancel to cancel")


def cancel(bot, update):
    global state
    is_admin, _ = get_admin(update.message.from_user)
    if not is_admin:
        return
    state[update.message.chat_id] = MAIN
    bot.sendMessage(update.message.chat_id,
                    text="Current operation canceled")

# Add all handlers to the dispatcher and run the bot
dp.addTelegramCommandHandler('start', help)
dp.addTelegramCommandHandler('help', help)
dp.addTelegramCommandHandler('add_admin', add_admin)
dp.addTelegramCommandHandler('remove_admin', remove_admin)
dp.addTelegramCommandHandler('add', add_scammer)
dp.addTelegramCommandHandler('remove', remove_scammer)
dp.addTelegramCommandHandler('cancel', cancel)
dp.addTelegramMessageHandler(message_handler)
dp.addErrorHandler(error)

start_bot(u)
u.idle()
