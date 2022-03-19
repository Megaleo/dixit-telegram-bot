from telegram import Update, InlineQueryResultPhoto, InputTextMessageContent
from telegram.ext import Updater, CallbackContext, CommandHandler, InlineQueryHandler
from uuid import uuid4
import sys
import logging

# Following tutorial in https://github.com/python-telegram-bot/python-telegram-bot/wiki/Extensions-%E2%80%93-Your-first-Bot

def start(update: Update, context: CallbackContext):
    # Run when user enters /start
    context.bot.send_message(chat_id=update.effective_chat.id, text="Let's play Dixit!")

def inline(update: Update, context: CallbackContext):
    results = []
    # for n in range(1, 10):
    #     results.append(
    #         InlineQueryResultPhoto(
    #             id = str(uuid4()),
    #             photo_url = f'https://raw.githubusercontent.com/jminuscula/dixit-online/master/cards/card_0000{n}.jpg',
    #             thumb_url = f'https://raw.githubusercontent.com/jminuscula/dixit-online/master/cards/card_0000{n}.jpg',
    #             title = f'Photo number {n}'
    #         )
    #     )
    results.append(
        InlineQueryResultPhoto(
            id = str(uuid4()),
            photo_url = f'https://nerdist.com/wp-content/uploads/2020/07/maxresdefault.jpg',
            thumb_url = f'https://www.kitchener.ca/en/images/structure/news_avatar.jpg',
            title = f'Rickzin'
        )
    )
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
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                     level=logging.INFO)
    with open('token.txt', 'r') as token_file:
        token = token_file.readline()[:-1] # Remove \n at the end
        run_bot(token)
