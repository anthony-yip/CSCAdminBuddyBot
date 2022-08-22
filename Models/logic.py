# bot functions
import telegram
from firebase_admin import db
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ConversationHandler
from datetime import datetime, date
from Models.database_functions import archive_and_split, who_is_not_around_today, dict_to_excel, create_parade_state
from Models.helper import *


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
    ref = db.reference("/user_chats")
    append_dict(ref, str(update.effective_chat.id), rank_name)
    off_balance_ref = db.reference("/off_balance")

    # todo anthony i found a bug here - joshua
    # if rank_name not in off_balance_ref:
    user_exists = True if off_balance_ref.order_by_key().equal_to(rank_name).get() else False
    if user_exists is False:
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
        "Type": urti
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