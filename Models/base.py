# bot functions
import telegram
from firebase_admin import db
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ConversationHandler
from Models.helper import *
# from io import BytesIO


def start(update, context):
    user_home_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Report Sick", callback_data='Report Sick')],
        [InlineKeyboardButton("Submit MC", callback_data='Submit MC')],
        [InlineKeyboardButton("Apply for Off/Leave", callback_data='Apply Off')]
    ])
    chat_id = update.effective_chat.id
    context.bot.send_message(chat_id=chat_id, text="Hi there! I'm AdminBuddyBot and I manage CSC's admin matters.")
    user_chats = db.reference("/user_chats").get()
    if str(chat_id) in user_chats:
        context.bot.send_message(chat_id=chat_id,
                                 text="What would you like to do today?", reply_markup=user_home_keyboard)
        return ConversationHandler.END
    else:
        context.bot.send_message(chat_id=chat_id, text="Let's get you started. What's your rank (e.g. 3SG)?")
        return REGISTERNAME


def cancel(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="Operation Cancelled. Type /start to try again.",
                             reply_markup=telegram.ReplyKeyboardRemove())
    return ConversationHandler.END


def register_name(update, context):
    context.user_data["Rank"] = update.message.text
    context.bot.send_message(chat_id=update.effective_chat.id, text="What's your full name?")
    # cross-check with nominal roll?
    return REGISTERFINISH


def register_finish(update, context):
    rank = context.user_data.pop("Rank")
    rank_name = f"{rank} {update.message.text.upper()}"
    chats_ref = db.reference("/user_chats")
    users_ref = db.reference("/user_chats/{0}".format(update.effective_chat.id))

    off_balance_ref = db.reference("/off_balance")
    user_off_ref = db.reference("/off_balance{0}".format(rank_name))

    # todo anthony i found a bug here - joshua
    # if rank_name not in off_balance_ref:
    # user_exists = True if off_balance_ref.order_by_key().equal_to(rank_name).get() else False
    if user_off_ref.get() is None or users_ref.get() is None:
        # user does not exist, therefore create entries
        append_dict(chats_ref, str(update.effective_chat.id), rank_name)     # create new user chat
        append_dict(off_balance_ref, rank_name, 0)      # create new off entry for said user

    if str(update.effective_chat.id) in db.reference("/user_chats").get():
        context.bot.send_message(chat_id=update.effective_chat.id, text=f"Successfully Registered as {rank_name}")
        user_home_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Report Sick", callback_data='Report Sick')],
            [InlineKeyboardButton("Submit MC", callback_data='Submit MC')]
        ])
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text="What would you like to do today?", reply_markup=user_home_keyboard)
        return ConversationHandler.END
    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text=f"Registration failed. Please try again")
        raise Exception('Failed to Register')


def dont_recognize(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text="I'm sorry, I don't recognize that input. Please try again.")
    return None
