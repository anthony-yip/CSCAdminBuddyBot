# Quick Reference:
# update.callback_query.data to obtain the pattern of the callback query (button press)
# update.message.text to obtain the text from an update
# remove markup(Keyboard):
# context.bot.edit_message_reply_markup(chat_id=update.effective_chat.id, message_id=update.effective_message.message_id)

# import all necessary modules
from telegram.ext import Updater
import logging
from telegram.ext import CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, Filters
import firebase_admin
from Models.private_info import credentials_path, database_url, telegram_token
from Models.logic import *


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

    award_off_conversation = ConversationHandler(
        entry_points=[CallbackQueryHandler(award_off_name, pattern="Award Off")],
        states={
            AWARD_OFF_NUMBER: [MessageHandler(Filters.regex("^[1-3A-Z]{3}"), award_off_number)],
            AWARD_OFF_UPDATE: [MessageHandler(Filters.regex("^[0-9]+"), award_off_update)]
        },
        fallbacks=[CommandHandler("cancel", cancel), MessageHandler(Filters.update, dont_recognize)]
    )

    dispatcher.add_handler(CallbackQueryHandler(rs_approved, pattern="Approved.*"))
    dispatcher.add_handler(location_tracking_conversation)
    dispatcher.add_handler(submit_mc_conversation)
    dispatcher.add_handler(rs_location_conversation)
    dispatcher.add_handler(register_conversation)
    dispatcher.add_handler(apply_off_conversation)
    dispatcher.add_handler(award_off_conversation)
    # this must be at the bottom due to handler priority
    dispatcher.add_handler(CommandHandler("cancel", cancel))
    dispatcher.add_handler(CommandHandler("admin", admin))
    dispatcher.add_handler(CallbackQueryHandler(admin_excel_choose, pattern="Export Excel"))
    dispatcher.add_handler(CallbackQueryHandler(admin_excel_export, pattern="Excel*"))
    dispatcher.add_handler(CallbackQueryHandler(parade_state, pattern="Generate Parade State"))
    # have to force stop the program to stop polling
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
