from datetime import datetime

from firebase_admin import db
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler

from Models.helper import OFF_SUCCESS, OFF_TYPE, OFF_END_DATE


def off_start_date(update, context):
    context.bot.edit_message_reply_markup(chat_id=update.effective_chat.id,
                                          message_id=update.effective_message.message_id)
    context.bot.send_message(chat_id=update.effective_chat.id, text="Start Date of Off? (DDMMYY format)")
    return OFF_END_DATE


def off_end_date(update, context):
    try:
        start_date = datetime.strptime(update.message.text, "%d%m%y").date()
    except(ValueError):
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text="Invalid date. Please try again.")
        return None
    else:
        context.user_data["OffStart"] = update.message.text
        context.user_data["OffStartDateObj"] = start_date
        context.bot.send_message(chat_id=update.effective_chat.id, text="End Date of Off? (DDMMYY format)")
        return OFF_TYPE


def off_type(update, context):
    start_date = context.user_data["OffStartDateObj"]
    try:
        end_date = datetime.strptime(update.message.text, "%d%m%y").date()
        context.user_data["OffEndDateObj"] = end_date
    except(ValueError):
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text="Invalid date. Please try again.")
        return None
    if end_date < start_date:
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text="Invalid date. Please try again.")
        return None
    context.user_data["OffEnd"] = update.message.text
    context.bot.send_message(chat_id=update.effective_chat.id, text="Is this Off or Leave?",
                             reply_markup=InlineKeyboardMarkup([
                                 [InlineKeyboardButton("Off", callback_data='OFFTYPEOff')],
                                 [InlineKeyboardButton("Leave", callback_data='OFFTYPELeave')]
                             ]))
    return OFF_SUCCESS


def off_success(update, context):
    context.bot.edit_message_reply_markup(chat_id=update.effective_chat.id,
                                          message_id=update.effective_message.message_id)
    start_date = context.user_data.pop("OffStart", "No Start Found")
    end_date = context.user_data.pop("OffEnd", "No End Found")
    start_date_object = context.user_data.pop("OffStartDateObj", None)
    end_date_object = context.user_data.pop("OffEndDateObj", None)
    number_of_off = (end_date_object - start_date_object).days + 1
    type = update.callback_query.data[7:]
    user_chats = db.reference("/user_chats").get()
    rank_name = user_chats[str(update.effective_chat.id)]
    rank = rank_name[:3]
    name = rank_name[4:]
    old_off = db.reference(f"/off_balance/{rank_name}").get()
    if type == "Off":
        if old_off >= number_of_off:
            db.reference(f"/off_balance/{rank_name}").set(old_off - number_of_off)
        else:
            context.bot.send_message(chat_id=update.effective_chat.id, text="Insufficient Off. Please try again.")
            return ConversationHandler.END
    context.bot.send_message(chat_id=db.reference("/core_chat").get(),
                             text=f"{rank_name} has applied {type} lasting from {start_date} to {end_date}.")
    off_ref = db.reference("/Off_Leave")
    off_entry = {
        "Rank": rank,
        "Name": name,
        "Start Date": start_date,
        "End Date": end_date,
        "Type": type
    }
    off_ref.push().set(off_entry)
    context.bot.send_message(chat_id=update.effective_chat.id, text=f"{type} Successfully Applied!")
    if type == "Off":
        context.bot.send_message(chat_id=update.effective_chat.id, text=
        f"{number_of_off} Off has been deducted from your balance. Your remaining balance is {old_off - number_of_off} Off.")
    return ConversationHandler.END