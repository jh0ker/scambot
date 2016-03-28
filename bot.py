import logging

from telegram.ext import Updater
from telegram import ParseMode, ReplyKeyboardMarkup, ReplyKeyboardHide
from telegram.utils.botan import Botan
from pony.orm import db_session, select, get

from credentials import TOKEN, BOTAN_TOKEN
from start_bot import start_bot
from database import db

from admin import Admin
from scammer import Scammer

# States the bot can have (maintained per chat id)
MAIN, ADD_SCAMMER, REMOVE_SCAMMER, ADD_ADMIN, REMOVE_ADMIN, PHONE_NR,\
    ACCOUNT_NR, BANK_NAME, REMARK, SEARCH, ADD_INFO = range(11)

options = {PHONE_NR: "Phone number", ACCOUNT_NR: "Account number",
           BANK_NAME: "Name of bank account owner", REMARK: "Admin remark"}

# Enable reverse lookup
for k, v in list(options.items()):
    options[v] = k

_grid = [[options[ACCOUNT_NR]],
         [options[BANK_NAME]],
         [options[PHONE_NR]],
         [options[REMARK]],
         ['/cancel']]

CAT_KEYBOARD = ReplyKeyboardMarkup(_grid, selective=True)

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
    admin = get(a for a in Admin if a.id is from_user.id)
    if admin:
        admin.first_name = from_user.first_name
        admin.last_name = from_user.last_name
        admin.username = from_user.username
    return admin


@db_session
def get_scammer(from_user):
    scammer = get(s for s in Scammer if s.id is from_user.id)
    if scammer:
        scammer.first_name = from_user.first_name
        scammer.last_name = from_user.last_name
        scammer.username = from_user.username
    return scammer


@db_session
def get_scammer_by_id(id):
    return get(s for s in Scammer if s.id is id)


def message_handler(bot, update):
    global state
    forward_from = update.message.forward_from
    chat_id = update.message.chat_id
    chat_state = state.get(chat_id, MAIN)
    reply = None
    reply_markup = ReplyKeyboardHide(selective=True)

    if forward_from:
        if chat_state is MAIN:
            scammer = get_scammer(forward_from)
            if scammer:
                reply = "This user has been registered as a scammer"
            else:
                reply = "This user has <b>not</b> been registered as a scammer"
        elif chat_state is ADD_SCAMMER:
            scammer = get_scammer(forward_from)
            if not scammer:
                with db_session:
                    scammer = Scammer(id=forward_from.id,
                                      first_name=forward_from.first_name,
                                      last_name=forward_from.last_name,
                                      username=forward_from.username)
                reply = "Successfully added scammer"
            else:
                reply = "Scammer was already added"

            reply += "\n\n%s\n\nAdd additional info?" % str(scammer)
            reply_markup = CAT_KEYBOARD
            state[chat_id] = [ADD_INFO, scammer.id]
        elif chat_state is REMOVE_SCAMMER:
            state[chat_id] = MAIN
            with db_session:
                scammer = get_scammer(forward_from)
                if scammer:
                    scammer.delete()
                    reply = "Successfully removed scammer"
                else:
                    reply = "This user is not a registered scammer"
        elif chat_state is ADD_ADMIN:
            state[chat_id] = MAIN
            admin = get_admin(forward_from)
            if not admin:
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
                admin = get_admin(forward_from)
                if admin and not admin.super_admin:
                    admin.delete()
                    reply = "Successfully removed admin"
                else:
                    reply = "This user is not an admin"
    elif isinstance(chat_state, list):  # Search or additional info
        with db_session:
            text = update.message.text

            if chat_state[0] is ADD_INFO and len(chat_state) is 2 or \
               chat_state[0] is SEARCH and len(chat_state) is 1:
                option = options[text]
                chat_state.append(option)
                state[chat_id] = chat_state
                reply = "Please enter " + update.message.text
            elif chat_state[0] is ADD_INFO:
                scammer = get_scammer_by_id(chat_state[1])
                if chat_state[2] is PHONE_NR:
                    scammer.phone_nr = text
                elif chat_state[2] is ACCOUNT_NR:
                    scammer.account_nr = text
                elif chat_state[2] is BANK_NAME:
                    scammer.bank_name = text
                elif chat_state[2] is REMARK:
                    scammer.remark = text
                chat_state.pop()  # one menu back
                state[chat_id] = chat_state
                reply_markup = CAT_KEYBOARD
                reply = "Add more additional info?"
            elif chat_state[0] is SEARCH:
                scammers = None
                if chat_state[1] is PHONE_NR:
                    scammers = select(s for s in Scammer if
                                      # s.phone_nr in text or
                                      text in s.phone_nr).limit(10)
                elif chat_state[1] is ACCOUNT_NR:
                    scammers = select(s for s in Scammer if
                                      # s.account_nr in text or
                                      text in s.account_nr).limit(10)
                elif chat_state[1] is BANK_NAME:
                    scammers = select(s for s in Scammer if
                                      # s.bank_name in text or
                                      text in s.bank_name).limit(10)
                elif chat_state[1] is REMARK:
                    scammers = select(s for s in Scammer if
                                      # s.remark in text or
                                      text in s.remark).limit(10)

                if scammers:
                    reply = "Search results (max. 10 results): \n\n" + \
                            "\n\n---\n\n".join(str(s) for s in scammers)
                else:
                    reply = "No search results"

                chat_state = MAIN
                state[chat_id] = chat_state

    if reply:
        bot.sendMessage(chat_id, text=reply, parse_mode=ParseMode.HTML,
                        reply_to_message_id=update.message.message_id,
                        reply_markup=reply_markup)


def add_scammer(bot, update):
    global state
    admin = get_admin(update.message.from_user)
    if not admin:
        return
    state[update.message.chat_id] = ADD_SCAMMER
    bot.sendMessage(update.message.chat_id,
                    text="Forward me a message of the scammer you want to add"
                         " or send /cancel to cancel")


def remove_scammer(bot, update):
    global state
    admin = get_admin(update.message.from_user)
    if not admin:
        return
    state[update.message.chat_id] = REMOVE_SCAMMER
    bot.sendMessage(update.message.chat_id,
                    text="Forward me a message of the user you want to remove"
                         " or send /cancel to cancel")


def add_admin(bot, update):
    global state
    admin = get_admin(update.message.from_user)
    if not admin or not admin.super_admin:
        return
    state[update.message.chat_id] = ADD_ADMIN
    bot.sendMessage(update.message.chat_id,
                    text="Forward me a message of the user you want to add"
                         " as admin or send /cancel to cancel")


def remove_admin(bot, update):
    global state
    admin = get_admin(update.message.from_user)
    if not admin or not admin.super_admin:
        return
    state[update.message.chat_id] = REMOVE_ADMIN
    bot.sendMessage(update.message.chat_id,
                    text="Forward me a message of the admin you want to remove"
                         " or send /cancel to cancel")


def cancel(bot, update):
    global state
    admin = get_admin(update.message.from_user)
    if not admin:
        return
    state[update.message.chat_id] = MAIN
    bot.sendMessage(update.message.chat_id,
                    text="Current operation canceled",
                    reply_markup=ReplyKeyboardHide())


def search(bot, update):
    global state
    state[update.message.chat_id] = [SEARCH]
    bot.sendMessage(update.message.chat_id,
                    text="Choose search category",
                    reply_markup=CAT_KEYBOARD)

# Add all handlers to the dispatcher and run the bot
dp.addTelegramCommandHandler('start', help)
dp.addTelegramCommandHandler('help', help)
dp.addTelegramCommandHandler('add_admin', add_admin)
dp.addTelegramCommandHandler('remove_admin', remove_admin)
dp.addTelegramCommandHandler('add', add_scammer)
dp.addTelegramCommandHandler('remove', remove_scammer)
dp.addTelegramCommandHandler('search', search)
dp.addTelegramCommandHandler('cancel', cancel)
dp.addTelegramMessageHandler(message_handler)
dp.addErrorHandler(error)

start_bot(u)
u.idle()
