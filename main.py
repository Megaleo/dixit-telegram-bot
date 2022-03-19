from telegram import Update, InlineQueryResultPhoto, InputTextMessageContent
from telegram.ext import (Updater, CallbackContext, CommandHandler, 
                          InlineQueryHandler)
from uuid import uuid4
from random import choices
import sys
import logging

# Following tutorial in 
# https://github.com/python-telegram-bot/python-telegram-bot
# /wiki/Extensions-%E2%80%93-Your-first-Bot

def start(update: Update, context: CallbackContext):
    # Run when user enters /start
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text="Let's play Dixit!")

def inline(update: Update, context: CallbackContext):
    # Supostamente roda quando o usuário faz um query inline, 
    # mas está se comportando bem mal

    def imagem_dixit_github(n):
        # Fetches the n-th image from the github image repo
        url_imagem = 'https://raw.githubusercontent.com/jminuscula/'\
                + f'dixit-online/master/cards/card_{n:0>5}.jpg'
        print(url_imagem)
        return InlineQueryResultPhoto(
                id = str(uuid4()),
                photo_url = url_imagem,
                thumb_url = url_imagem,
                title = f"card {n} in the player's hand")
        
    results = [imagem_dixit_github(n) for n in choices(range(1, 101), k=6)]
    print()
    update.inline_query.answer(results)

def run_bot(token):
    updater = Updater(token)
    dispatcher = updater.dispatcher

    # Add start handler
    start_handler = CommandHandler('start', start)
    dispatcher.add_handler(start_handler)

    # Add inline handler
    inline_handler = InlineQueryHandler(inline)
    dispatcher.add_handler(inline_handler)

    # Start the bot
    updater.start_polling()

    updater.idle()

if __name__ == '__main__':
    logging_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(format=logging_format, level=logging.INFO)
    with open('token.txt', 'r') as token_file:
        token = token_file.readline()[:-1] # Remove \n at the end
        run_bot(token)
