# Quick Reference:
# update.callback_query.data to obtain the pattern of the callback query (button press)
# update.message.text to obtain the text from an update
# context.bot.edit_message_reply_markup(chat_id=update.effective_chat.id,
#                                       message_id=update.effective_message.message_id): remove markup (Keyboard)


# import all necessary modules
import telegram
from telegram.ext import Updater
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import logging
from telegram.ext import CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, Filters
import firebase_admin
from firebase_admin import db
from private_info import core_chat, user_chats, credentials_path, database_url, telegram_token
import json
from datetime import datetime, date

# so ConversationHandler doesn't throw errors
MC_END_DATE, MC_URTI, MC_SUCCESS = range(3)
OFF_END_DATE, OFF_TYPE, OFF_SUCCESS = range(3)
RSLOCATION, RSTYPE = range(2)
REGISTERNAME, REGISTERFINISH = range(2)
LTREACHCLINIC, LTLEFTCLINIC, LTREACHHOUSE = range(3)


# TODO: handle rank promotion
# helper functions
def append_dict(ref, key, value):
    _dict = ref.get()
    _dict[key] = value
    return ref.set(_dict)


# bot functions
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


# def admin(update, context):
#     chat_id = update.effective_chat.id
#     if chat_id == db.reference("/core_chat").get():
#         admin_keyboard = InlineKeyboardMarkup([
#             [InlineKeyboardButton("Export Excel", callback_data='Export Excel')],
#             [InlineKeyboardButton("Generate Parade State", callback_data='Generate Parade State')],
#             [InlineKeyboardButton("Award Off", callback_data='Award Off')]
#         ])
#         context.bot.send_message(chat_id=chat_id,
#                                  text="What would you like to do today?", reply_markup=admin_keyboard)
#     else:
#         context.bot.send_message(chat_id=chat_id, text="Only admins can use this command.")
#         return -1


def cancel(update, context):
    # TODO: this doesn't really work quite right yet.
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
    ref = db.reference("/user_chats")
    append_dict(ref, str(update.effective_chat.id), rank_name)
    off_balance_ref = db.reference("/off_balance")
    if rank_name not in off_balance_ref:
        append_dict(off_balance_ref, rank_name, 0)
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


# report sick chunk START
def rs_choose_location(update, context):
    chat_id = update.effective_chat.id
    context.bot.edit_message_reply_markup(chat_id=update.effective_chat.id,
                                          message_id=update.effective_message.message_id)
    where = InlineKeyboardMarkup([[InlineKeyboardButton("JCMC", callback_data='JCMC'),
                                   InlineKeyboardButton("External clinic", callback_data='External clinic')]])
    context.bot.send_message(chat_id=chat_id,
                             text="Where are you reporting sick?", reply_markup=where)
    return RSTYPE


def rs_input_location(update, context):
    context.bot.edit_message_reply_markup(chat_id=update.effective_chat.id,
                                          message_id=update.effective_message.message_id)
    # In response to 'External clinic' callback query
    chat_id = update.effective_chat.id
    context.bot.send_message(chat_id=chat_id,
                             text="What's the name of the clinic?")
    return RSLOCATION


def rs_send_for_approval(update, context):
    chat_id = update.effective_chat.id
    # JCMC = callback_query, external clinic name = message
    if update.callback_query:
        rs_location = update.callback_query.data
        context.bot.edit_message_reply_markup(chat_id=chat_id, message_id=update.effective_message.message_id)
    elif update.message:
        rs_location = update.message.text
    context.user_data["RSLocation"] = rs_location
    context.bot.send_message(chat_id=chat_id, text="Please wait for the command team's approval.")
    context.bot.sendDocument(chat_id=chat_id,
                             document="https://c.tenor.com/ycKJas-YT0UAAAAM/im-waiting-aki-and-paw-paw.gif")
    approve_keyboard = InlineKeyboardMarkup([
        # sends the requesting person's chat id through callback data
        [InlineKeyboardButton("Approve", callback_data=f'Approved{chat_id}')]
    ])
    user_chats = db.reference("/user_chats").get()
    context.bot.send_message(chat_id=db.reference("/core_chat").get(),
                             text=f"{user_chats[str(chat_id)]} is requesting to report sick at {rs_location}. Approve?",
                             reply_markup=approve_keyboard)
    return -1


def rs_approved(update, context):
    relevant_chat_id = int(update.callback_query.data[8:])
    user_chats = db.reference("/user_chats").get()
    context.bot.send_message(chat_id=db.reference("/core_chat").get(),
                             text=f"Request Approved for {user_chats[str(relevant_chat_id)]}",
                             reply_markup=telegram.ReplyKeyboardRemove())
    context.bot.edit_message_reply_markup(chat_id=db.reference("/core_chat").get(),
                                          message_id=update.effective_message.message_id)
    context.bot.send_message(chat_id=relevant_chat_id,
                             text="Your request has been approved.")
    context.bot.send_message(chat_id=relevant_chat_id,
                             text=f"Press this button once you leave!",
                             reply_markup=InlineKeyboardMarkup(
                                 [[InlineKeyboardButton("Left!", callback_data='Left House!')]]))


# report sick chunk END

# location tracking chunk START
def time_left_house(update, context):
    user_chats = db.reference("/user_chats").get()
    context.bot.delete_message(update.effective_chat.id, update.effective_message.message_id)
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text="Press this button once you reach the clinic!",
                             reply_markup=InlineKeyboardMarkup(
                                 [[InlineKeyboardButton("Reached!", callback_data='Reached Clinic!')]]))
    context.bot.send_message(chat_id=db.reference("/core_chat").get(),
                             text=f"{user_chats[str(update.effective_chat.id)]} has left the house/coyline at {datetime.now().strftime('%H%M')}.")
    return LTREACHCLINIC


def time_reached_clinic(update, context):
    user_chats = db.reference("/user_chats").get()
    context.bot.delete_message(update.effective_chat.id, update.effective_message.message_id)
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text="Press this button once you leave the clinic!",
                             reply_markup=InlineKeyboardMarkup(
                                 [[InlineKeyboardButton("Left!", callback_data='Left Clinic!')]]))
    context.bot.send_message(chat_id=db.reference("/core_chat").get(),
                             text=f"{user_chats[str(update.effective_chat.id)]} has reached the clinic at {datetime.now().strftime('%H%M')}.")
    return LTLEFTCLINIC


def time_left_clinic(update, context):
    user_chats = db.reference("/user_chats").get()
    context.bot.delete_message(update.effective_chat.id, update.effective_message.message_id)
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text="Press this button once you reach back!",
                             reply_markup=InlineKeyboardMarkup(
                                 [[InlineKeyboardButton("Reached!", callback_data='Reached House!')]]))
    context.bot.send_message(chat_id=db.reference("/core_chat").get(),
                             text=f"{user_chats[str(update.effective_chat.id)]} has left the clinic at {datetime.now().strftime('%H%M')}.")
    return LTREACHHOUSE


def time_reached_house(update, context):
    user_chats = db.reference("/user_chats").get()
    context.bot.delete_message(update.effective_chat.id, update.effective_message.message_id)
    context.bot.send_message(chat_id=db.reference("/core_chat").get(),
                             text=f"{user_chats[str(update.effective_chat.id)]} has reached their house/coyline at {datetime.now().strftime('%H%M')}.")
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text=f"Submit MC or Status:",
                             reply_markup=InlineKeyboardMarkup(
                                 [[InlineKeyboardButton("Submit MC", callback_data='Submit MC')]]))
    return -1


# location tracking chunk END

# submit mc chunk START
def mc_start_date(update, context):
    context.bot.edit_message_reply_markup(chat_id=update.effective_chat.id,
                                          message_id=update.effective_message.message_id)
    context.bot.send_message(chat_id=update.effective_chat.id, text="Start Date of MC? (DDMMYY format)")
    return MC_END_DATE


def mc_end_date(update, context):
    try:
        start_date = datetime.strptime(update.message.text, "%d%m%y").date()
    except(ValueError):
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text="Invalid date. Please try again.")
        return None
    if start_date > date.today():
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text="Invalid date. Please try again.")
        return None
    else:
        context.user_data["MCStart"] = update.message.text
        context.user_data["MCStartDateObj"] = start_date
        context.bot.send_message(chat_id=update.effective_chat.id, text="End Date of MC? (DDMMYY format)")
        return MC_URTI


def mc_urti(update, context):
    try:
        end_date = datetime.strptime(update.message.text, "%d%m%y").date()
    except(ValueError):
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text="Invalid date. Please try again.")
        return None
    if end_date < context.user_data.pop("MCStartDateObj", date.today()):
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text="Invalid date. Please try again.")
        return None
    context.user_data["MCEnd"] = update.message.text
    context.bot.send_message(chat_id=update.effective_chat.id, text="Do you have URTI symptoms?",
                             reply_markup=InlineKeyboardMarkup([
                                 [InlineKeyboardButton("Yes", callback_data='MCURTIYes')],
                                 [InlineKeyboardButton("No", callback_data='MCURTINo')]
                             ]))
    return MC_SUCCESS


def mc_success(update, context):
    context.bot.edit_message_reply_markup(chat_id=update.effective_chat.id,
                                          message_id=update.effective_message.message_id)
    start_date = context.user_data.pop("MCStart", "No Start Found")
    end_date = context.user_data.pop("MCEnd", "No End Found")
    urti = update.callback_query.data == "MCURTIYes"
    urti_message = "URTI" if urti else "Non-URTI"
    user_chats = db.reference("/user_chats").get()
    rank_name = user_chats[str(update.effective_chat.id)]
    rank = rank_name[:3]
    name = rank_name[4:]
    context.bot.send_message(chat_id=db.reference("/core_chat").get(),
                             text=f"{rank_name} has submitted an MC({urti_message}) lasting from {start_date} to {end_date}.")
    # submit MC entry to database
    mc_ref = db.reference("/MC")
    mc_entry = {
        "Rank": rank,
        "Name": name,
        "Start Date": start_date,
        "End Date": end_date,
        "URTI?": urti
    }
    mc_ref.push().set(mc_entry)
    context.bot.send_message(chat_id=update.effective_chat.id, text="MC Successfully Submitted!")
    return ConversationHandler.END


# submit mc chunk END

def dont_recognize(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text="I'm sorry, I don't recognize that input. Please try again.")
    return None


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


def main():
    # logging for exception handling
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.INFO)
    # firebase stuff
    cred_obj = firebase_admin.credentials.Certificate(credentials_path)
    firebase_admin.initialize_app(cred_obj, {
        'databaseURL': database_url
    })
    # create updater and all all relevant dispatchers
    updater = Updater(token=telegram_token,
                      use_context=True)
    dispatcher = updater.dispatcher
    apply_off_conversation = ConversationHandler(
        entry_points=[CallbackQueryHandler(off_start_date, pattern="Apply Off")],
        states={
            OFF_END_DATE: [MessageHandler(Filters.regex("^[0-3][0-9][0-1][0-9][0-9][0-9]$"), off_end_date)],
            OFF_TYPE: [MessageHandler(Filters.regex("^[0-3][0-9][0-1][0-9][0-9][0-9]$"), off_type)],
            OFF_SUCCESS: [CallbackQueryHandler(off_success, pattern="OFFTYPE*")]
        },
        fallbacks=[CommandHandler("cancel", cancel), MessageHandler(Filters.update, dont_recognize)]
    )
    submit_mc_conversation = ConversationHandler(
        entry_points=[CallbackQueryHandler(mc_start_date, pattern="Submit MC")],
        states={
            MC_END_DATE: [MessageHandler(Filters.regex("^[0-3][0-9][0-1][0-9][0-9][0-9]$"), mc_end_date)],
            MC_URTI: [MessageHandler(Filters.regex("^[0-3][0-9][0-1][0-9][0-9][0-9]$"), mc_urti)],
            MC_SUCCESS: [CallbackQueryHandler(mc_success, pattern="MCURTI*")]
        },
        fallbacks=[CommandHandler("cancel", cancel), MessageHandler(Filters.update, dont_recognize)]
    )
    rs_location_conversation = ConversationHandler(
        entry_points=[CallbackQueryHandler(rs_choose_location, pattern="Report Sick")],
        states={
            RSTYPE: [CallbackQueryHandler(rs_input_location, pattern="External clinic"),
                     CallbackQueryHandler(rs_send_for_approval, pattern="JCMC")],
            RSLOCATION: [MessageHandler(Filters.text & (~Filters.command), rs_send_for_approval)]
        },
        fallbacks=[CommandHandler("cancel", cancel), MessageHandler(Filters.update, dont_recognize)]
    )
    location_tracking_conversation = ConversationHandler(
        entry_points=[CallbackQueryHandler(time_left_house, pattern="Left House!")],
        states={
            LTREACHCLINIC: [CallbackQueryHandler(time_reached_clinic, pattern="Reached Clinic!")],
            LTLEFTCLINIC: [CallbackQueryHandler(time_left_clinic, pattern="Left Clinic!")],
            LTREACHHOUSE: [CallbackQueryHandler(time_reached_house, pattern="Reached House!")]
        },
        fallbacks=[CommandHandler("cancel", cancel), MessageHandler(Filters.update, dont_recognize)]
    )
    register_conversation = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            # might need a custom filter for specific ranks
            REGISTERNAME: [MessageHandler(Filters.regex("^[1-3A-Z]{3}$"), register_name)],
            REGISTERFINISH: [MessageHandler(Filters.text & (~Filters.command), register_finish)]
        },
        fallbacks=[CommandHandler("cancel", cancel), MessageHandler(Filters.update, dont_recognize)]
    )
    dispatcher.add_handler(CallbackQueryHandler(rs_approved, pattern="Approved.*"))
    dispatcher.add_handler(location_tracking_conversation)
    dispatcher.add_handler(submit_mc_conversation)
    dispatcher.add_handler(rs_location_conversation)
    dispatcher.add_handler(register_conversation)
    dispatcher.add_handler(apply_off_conversation)
    # this must be at the bottom due to handler priority
    dispatcher.add_handler(CommandHandler("cancel", cancel))
    # have to force stop the program to stop polling
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
