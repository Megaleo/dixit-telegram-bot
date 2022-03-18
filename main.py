from telegram import Update
from telegram.ext import Updater, CallbackContext, CommandHandler
import sys
import logging

# Following tutorial in https://github.com/python-telegram-bot/python-telegram-bot/wiki/Extensions-%E2%80%93-Your-first-Bot

def start(update: Update, context: CallbackContext):
    # Run when user enters /start
    context.bot.send_message(chat_id=update.effective_chat.id, text="Let's play Dixit!")

def run_bot(token):
    updater = Updater(token)
    dispatcher = updater.dispatcher

    # Add start handler
    start_handler = CommandHandler('start', start)
    dispatcher.add_handler(start_handler)

    # Start the bot
    updater.start_polling()

if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                     level=logging.INFO)
    token = sys.argv[1]
    run_bot(token)
