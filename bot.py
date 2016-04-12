import logging
from datetime import datetime
from io import BytesIO, BufferedReader

from telegram.ext import Updater
from telegram.ext.dispatcher import run_async
from telegram import ParseMode, ReplyKeyboardMarkup, ReplyKeyboardHide, \
    ChatAction, ForceReply
from telegram.utils.botan import Botan
from pony.orm import db_session, select

from credentials import TOKEN, BOTAN_TOKEN
from start_bot import start_bot
from database import db

from admin import Admin
from scammer import Scammer
from reporter import Reporter

# States the bot can have (maintained per chat id)
MAIN, ADD_SCAMMER, REMOVE_SCAMMER, ADD_ADMIN, REMOVE_ADMIN, PHONE_NR,\
    ACCOUNT_NR, BANK_NAME, REMARK, SEARCH, ADD_INFO, EDIT = range(12)

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
DB_NAME = 'bot.sqlite'

state = dict()
last_search_query = dict()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG)
logger = logging.getLogger(__name__)

u = Updater(TOKEN)
dp = u.dispatcher

db.bind('sqlite', DB_NAME, create_db=True)
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

help_text = "This bot keeps a database of known scammers by recording their " \
            "phone number, bank account number and name.\n\n" \
            "<b>Usage:</b>\n" \
            "/search - Search the database for reports\n\n" \
            "Donations via BTC are welcome: 1EPu17mBM2zw4LcupURgwsAuFeKQrTa1jy"

admin_help_text = "\n\n" \
                  "<b>Admin commands:</b>\n" \
                  "/new - Add a new scammer report\n" \
                  "/edit - Edit an existing report\n" \
                  "/delete - Delete a scammer report\n" \
                  "/cancel - Cancel current operation"

super_admin_help_text = "\n\n" \
                        "<b>Super Admin commands:</b>\n" \
                        "/add_admin - Register a new admin\n" \
                        "/remove_admin - Remove an admin\n" \
                        "/download_database - Download complete database"


def error(bot, update, error):
    """ Simple error handler """
    logger.exception(error)


def help(bot, update):
    """ Handler for the /help command """
    from_user = update.message.from_user
    chat_id = update.message.chat_id

    with db_session:
        admin = get_admin(from_user)

    text = help_text

    if admin:
        text += admin_help_text
        if admin.super_admin:
            text += super_admin_help_text

    bot.sendMessage(chat_id,
                    text=text,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True)


def get_admin(from_user):
    admin = Admin.get(id=from_user.id)
    if admin:
        admin.first_name = from_user.first_name
        admin.last_name = from_user.last_name
        admin.username = from_user.username
    return admin


def get_reporter(from_user):
    reporter = Reporter.get(id=from_user.id)
    if reporter:
        reporter.first_name = from_user.first_name
        reporter.last_name = from_user.last_name
        reporter.username = from_user.username
    return reporter


def message_handler(bot, update):
    global state
    forward_from = update.message.forward_from
    chat_id = update.message.chat_id
    chat_state = state.get(chat_id, MAIN)
    reply = None
    reply_markup = ReplyKeyboardHide(selective=True)

    with db_session:
        if chat_state is ADD_SCAMMER and forward_from:
            reporter = get_reporter(forward_from)
            if not reporter:
                reporter = Reporter(id=forward_from.id,
                                    first_name=forward_from.first_name,
                                    last_name=forward_from.last_name,
                                    username=forward_from.username)
                track(update, 'new_reporter')

            scammer = Scammer(added_by=get_admin(update.message.from_user))
            scammer.reported_by.add(reporter)
            track(update, 'new_report')
            db.commit()

            reply = "Created report <b>#%d</b>! Please enter scammer " \
                    "information:" % scammer.id
            reply_markup = CAT_KEYBOARD
            state[chat_id] = [ADD_INFO, scammer.id]

        elif chat_state is EDIT:
            try:
                report_id = int(update.message.text.replace('#', ''))
            except ValueError:
                reply = "Not a valid report number. Try again or use " \
                        "/cancel to abort."
            else:
                scammer = Scammer.get(id=report_id)

                if scammer:
                    reply = "%s\n\nPlease enter new " \
                            "scammer information:" % str(scammer)
                    reply_markup = CAT_KEYBOARD
                    state[chat_id] = [ADD_INFO, scammer.id]
                else:
                    reply = "Could not find report number. Try again or " \
                            "use /cancel to abort."

        elif chat_state is REMOVE_SCAMMER:
            try:
                report_id = int(update.message.text.replace('#', ''))
            except ValueError:
                reply = "Not a valid report number. Try again or use " \
                        "/cancel to abort."
            else:
                scammer = Scammer.get(id=report_id)
                if scammer:
                    scammer.delete()
                    reply = "Deleted report!"
                    del state[chat_id]
                else:
                    reply = "Could not find report number. Try again or " \
                            "use /cancel to abort."
                    reply_markup = ForceReply()

        elif chat_state is ADD_ADMIN and forward_from:
            admin = get_admin(forward_from)
            if not admin:
                Admin(id=forward_from.id,
                      first_name=forward_from.first_name,
                      last_name=forward_from.last_name,
                      username=forward_from.username)
                reply = "Successfully added admin"
            else:
                reply = "This user is already an admin"

            del state[chat_id]

        elif chat_state is REMOVE_ADMIN and forward_from:
            admin = get_admin(forward_from)
            if admin and not admin.super_admin:
                admin.delete()
                reply = "Successfully removed admin"
            else:
                reply = "This user is not an admin"

            del state[chat_id]

        elif chat_state is SEARCH:
            text = update.message.text
            scammers = select(s for s in Scammer if
                              text in s.phone_nr or
                              text in s.account_nr or
                              text in s.bank_name or
                              text in s.remark).limit(11)

            if scammers:
                reply = "Search results: \n\n" + \
                        "\n\n".join(str(s) for s in scammers[:10])
            else:
                reply = "No search results"

            if len(scammers) > 10:
                reply += "\n\n" \
                         "There were more than 10 results. " \
                         "Use /all to download a list of the first max. 100 " \
                         "results."
                last_search_query[chat_id] = (text, datetime.now())

            del state[chat_id]
            track(update, 'search')

        elif isinstance(chat_state, list):  # Additional info
            text = update.message.text

            if chat_state[0] is ADD_INFO and len(chat_state) is 2:
                option = options[text]
                chat_state.append(option)
                state[chat_id] = chat_state
                reply = "Please enter " + update.message.text
                reply_markup = ForceReply()
            elif chat_state[0] is ADD_INFO:
                    scammer = Scammer.get(id=chat_state[1])
                    text = update.message.text
                    category = chat_state[2]
                    if category is PHONE_NR:
                        scammer.phone_nr = text
                    elif category is ACCOUNT_NR:
                        scammer.account_nr = text
                    elif category is BANK_NAME:
                        scammer.bank_name = text
                    elif category is REMARK:
                        scammer.remark = text
                    chat_state.pop()  # one menu back
                    state[chat_id] = chat_state
                    reply_markup = CAT_KEYBOARD
                    reply = "Add more info or send /cancel if you're done."

    if reply:
        bot.sendMessage(chat_id, text=reply, parse_mode=ParseMode.HTML,
                        reply_to_message_id=update.message.message_id,
                        reply_markup=reply_markup)


@run_async
def track(update, event_name):
    if botan:
        botan.track(message=update.message, event_name=event_name)


def add_scammer(bot, update):
    global state
    with db_session:
        admin = get_admin(update.message.from_user)
    if not admin:
        return
    state[update.message.chat_id] = ADD_SCAMMER
    bot.sendMessage(update.message.chat_id,
                    text="Forward me a message of the user that is reporting "
                         "the scammer or use /cancel to cancel")


def remove_scammer(bot, update):
    global state
    with db_session:
        admin = get_admin(update.message.from_user)
    if not admin:
        return
    state[update.message.chat_id] = REMOVE_SCAMMER
    bot.sendMessage(update.message.chat_id,
                    text="Please send the Report # of the report you wish "
                         "to remove or send /cancel to cancel",
                    reply_markup=ForceReply())


def edit_scammer(bot, update):
    global state
    with db_session:
        admin = get_admin(update.message.from_user)
    if not admin:
        return
    state[update.message.chat_id] = EDIT
    bot.sendMessage(update.message.chat_id,
                    text="Please send the Report # of the report you wish "
                         "to edit or send /cancel to cancel",
                    reply_markup=ForceReply())


def confirm_scammer(bot, update, groupdict):
    chat_id = update.message.chat_id
    scammer_id = int(groupdict['scammer'])
    from_user = update.message.from_user

    with db_session:
        scammer = Scammer.get(id=scammer_id)

        if not scammer:
            reply = "Report not found!"

        else:
            reporter = get_reporter(from_user)

            if not reporter:
                reporter = Reporter(id=from_user.id,
                                    first_name=from_user.first_name,
                                    last_name=from_user.last_name,
                                    username=from_user.username)
                track(update, 'new_reporter')

            scammer.reported_by.add(reporter)
            reply = "Report confirmed!"

    bot.sendMessage(chat_id, text=reply)


def add_admin(bot, update):
    global state
    with db_session:
        admin = get_admin(update.message.from_user)
    if not admin or not admin.super_admin:
        return
    state[update.message.chat_id] = ADD_ADMIN
    bot.sendMessage(update.message.chat_id,
                    text="Forward me a message of the user you want to add"
                         " as admin or send /cancel to cancel")


def remove_admin(bot, update):
    global state
    with db_session:
        admin = get_admin(update.message.from_user)
    if not admin or not admin.super_admin:
        return
    state[update.message.chat_id] = REMOVE_ADMIN
    bot.sendMessage(update.message.chat_id,
                    text="Forward me a message of the admin you want to remove"
                         " or send /cancel to cancel")


def cancel(bot, update):
    try:
        del state[update.message.chat_id]
    finally:
        bot.sendMessage(update.message.chat_id,
                        text="Current operation canceled",
                        reply_markup=ReplyKeyboardHide())


def search(bot, update):
    global state
    state[update.message.chat_id] = SEARCH
    bot.sendMessage(update.message.chat_id,
                    text="Enter search query:",
                    reply_markup=ForceReply())


def download_all(bot, update):
    global last_search_query
    chat_id = update.message.chat_id
    query_tuple = last_search_query.get(update.message.chat_id, None)
    if not query_tuple:
        bot.sendMessage(update.message.chat_id,
                        text="Sorry, results are only preserved for 15 "
                             "minutes. Please use /search to start a new "
                             "search.")
    else:
        bot.sendChatAction(chat_id, action=ChatAction.UPLOAD_DOCUMENT)
        query = query_tuple[0]
        with db_session:
            scammers = select(s for s in Scammer if
                              query in s.phone_nr or
                              query in s.account_nr or
                              query in s.bank_name or
                              query in s.remark).limit(100)

            content = "\r\n\r\n".join(str(s) for s in scammers)

        file = BytesIO(content.encode())
        bot.sendDocument(chat_id, document=BufferedReader(file),
                         filename='search.txt')


def download_db(bot, update):
    chat_id = update.message.chat_id
    global state
    with db_session:
        admin = get_admin(update.message.from_user)
    if not admin or not admin.super_admin:
        return
    bot.sendChatAction(chat_id, action=ChatAction.UPLOAD_DOCUMENT)
    bot.sendDocument(chat_id, document=open(DB_NAME, 'rb'),
                     filename='scammers.sqlite')


# Add all handlers to the dispatcher and run the bot
dp.addTelegramCommandHandler('start', help)
dp.addTelegramCommandHandler('help', help)
dp.addTelegramCommandHandler('add_admin', add_admin)
dp.addTelegramCommandHandler('remove_admin', remove_admin)
dp.addTelegramCommandHandler('new', add_scammer)
dp.addTelegramCommandHandler('edit', edit_scammer)
dp.addTelegramCommandHandler('delete', remove_scammer)
dp.addTelegramCommandHandler('search', search)
dp.addTelegramCommandHandler('all', download_all)
dp.addTelegramCommandHandler('download_database', download_db)
dp.addTelegramCommandHandler('cancel', cancel)
dp.addTelegramRegexHandler(r'^/confirm_(?P<scammer>\d+)$', confirm_scammer)
dp.addTelegramMessageHandler(message_handler)
dp.addErrorHandler(error)

start_bot(u)
u.idle()
