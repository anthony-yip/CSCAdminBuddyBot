from datetime import datetime

from firebase_admin import db
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ConversationHandler

from Models.database_functions import archive_and_split, dict_to_excel, who_is_not_around_today, create_parade_state
from Models.helper import AWARD_OFF_UPDATE, AWARD_OFF_NUMBER


def admin(update, context):
    chat_id = update.effective_chat.id
    if chat_id == db.reference("/core_chat").get():
        # conduct archiving
        mc = db.reference("/MC").get()
        mc_main, mc_archive = archive_and_split(mc)
        db.reference("/MC").set(mc_main)
        db.reference("/MC_Archive").set(mc_archive)
        off = db.reference("/Off_Leave").get()
        off_main, off_archive = archive_and_split(off)
        db.reference("/Off_Leave").set(off_main)
        db.reference("/Off_Leave_Archive").set(off_archive)
        admin_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Export Excel", callback_data='Export Excel')],
            [InlineKeyboardButton("Generate Parade State", callback_data='Generate Parade State')],
            [InlineKeyboardButton("Award Off", callback_data='Award Off')]
        ])
        context.bot.send_message(chat_id=chat_id,
                                 text="What would you like to do today?", reply_markup=admin_keyboard)
    else:
        context.bot.send_message(chat_id=chat_id, text="Only admins can use this command.")
        return -1


def admin_excel_choose(update, context):
    context.bot.edit_message_reply_markup(chat_id=update.effective_chat.id,
                                          message_id=update.effective_message.message_id)
    choose_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("MC", callback_data='ExcelMC')],
        [InlineKeyboardButton("MC Archive", callback_data='ExcelMC_Archive')],
        [InlineKeyboardButton("Off/Leave", callback_data='ExcelOff_Leave')],
        [InlineKeyboardButton("Off/Leave Archive", callback_data='ExcelOff_Leave_Archive')]
    ])
    context.bot.send_message(chat_id=update.effective_chat.id,
                         text="Which would you like to export?", reply_markup=choose_keyboard)


def admin_excel_export(update, context):
    context.bot.edit_message_reply_markup(chat_id=update.effective_chat.id,
                                          message_id=update.effective_message.message_id)
    query_type = update.callback_query.data[5:]
    query_dict = db.reference(f"/{query_type}").get()
    name = f"{query_type} Query at {datetime.now().strftime('%d%m%y-%H%M%S')}.xlsx"
    print(name)
    dict_to_excel(query_dict, name)
    file = open(name, 'rb')
    context.bot.send_document(update.effective_chat.id, document=file)
    file.close()


def parade_state(update, context):
    context.bot.edit_message_reply_markup(chat_id=update.effective_chat.id,
                                          message_id=update.effective_message.message_id)
    mc = who_is_not_around_today(db.reference(f"/MC").get())
    off_leave = who_is_not_around_today(db.reference(f"/Off_Leave").get())
    context.bot.send_message(chat_id=update.effective_chat.id, text=create_parade_state(mc, off_leave))


def award_off_name(update, context):
    context.bot.edit_message_reply_markup(chat_id=update.effective_chat.id,
                                          message_id=update.effective_message.message_id)
    context.bot.send_message(chat_id=update.effective_chat.id, text="Who would you like to award off to?")
    return AWARD_OFF_NUMBER


def award_off_number(update, context):
    name = update.message.text
    if name not in db.reference("/off_balance").get():
        context.bot.send_message(chat_id=update.effective_chat.id, text="Invalid name. Please try again")
        return None
    else:
        context.chat_data["Award Off"] = name
        context.bot.send_message(chat_id=update.effective_chat.id, text="How many off?")
        return AWARD_OFF_UPDATE


def award_off_update(update, context):
    number = update.message.text
    name = context.chat_data.pop("Award Off")
    ref = db.reference(f"/off_balance/{name}")
    old_off = ref.get()
    ref.set(old_off + int(number))
    context.bot.send_message(chat_id=update.effective_chat.id, text=f"{number} Off awarded to {name}. Their new balance is {old_off + int(number)} Off.")
    return ConversationHandler.END
