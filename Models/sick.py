# report sick chunk START
from datetime import datetime, date

import telegram
from firebase_admin import db
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler

from Models.helper import RSLOCATION, RSTYPE, MC_UPLOAD, MC_URTI, MC_END_DATE, LTREACHHOUSE, LTLEFTCLINIC, LTREACHCLINIC


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
    # return MC_SUCCESS
    return MC_UPLOAD


def mc_success(update, context):
    context.bot.edit_message_reply_markup(chat_id=update.effective_chat.id,
                                          message_id=update.effective_message.message_id)
    rs_location = context.user_data["RSLocation"]
    submitted_date = str(datetime.strptime(str(datetime.now()), "%d%m%y").date())
    start_date = context.user_data.pop("MCStart", "No Start Found")
    end_date = context.user_data.pop("MCEnd", "No End Found")
    urti = "URTI" if update.callback_query.data == "MCURTIYes" else "Non-URTI"
    user_chats = db.reference("/user_chats").get()
    rank_name = user_chats[str(update.effective_chat.id)]
    rank = rank_name[:3]
    name = rank_name[4:]
    context.bot.send_message(chat_id=db.reference("/core_chat").get(),
                             text=f"{rank_name} has submitted an MC({urti}) lasting from {start_date} to {end_date}.")
    # submit MC entry to database
    mc_ref = db.reference("/MC")
    mc_entry = {
        "Rank": rank,
        "Name": name,
        "Start Date": start_date,
        "End Date": end_date,
        "Type": urti,
        "Location": rs_location,
        "Submitted Date": submitted_date
    }
    mc_ref.push().set(mc_entry)
    context.bot.send_message(chat_id=update.effective_chat.id, text="MC Successfully Submitted!")
    return ConversationHandler.END


# submit mc chunk END

