from telegram import Update, InlineQueryResultPhoto, InputTextMessageContent
from telegram.ext import (Updater, CallbackContext, CommandHandler,
                          InlineQueryHandler)
from uuid import uuid4
from random import choices
import sys
import logging

import game

# Following tutorial in
# https://github.com/python-telegram-bot/python-telegram-bot-wiki/Extensions-%E2%80%93-Your-first-Bot


def start_game_callback(update, context):
    '''Command callback. When /startgame is called, it does the following:
    1. Creates a default DixitGame instance and stores it in context.chat_data
    (See more about this in https://github.com/python-telegram-bot/python-telegram-bot/wiki/Storing-bot,-user-and-chat-related-data#chat-migration ,
    and about making it persistent in the future in https://github.com/python-telegram-bot/python-telegram-bot/wiki/Making-your-bot-persistent )
    2. Loads cards into game
    3. Sets this user as master
    4. Joins master user to the game
    '''
    cards = [] # Load cards here
    dixit_game = game.DixitGame(cards = cards)
    context.chat_data['dixit_game'] = dixit_game

    user_master = update.message.from_user
    context.chat_data['master'] = user_master
    master_player = game.Player(user_master, hand_cards=[])
    dixit_game.add_player(master_player)

    context.bot.send_message(chat_id=update.effective_chat.id,
                             text="Let's play Dixit!\n"\
                             + f"The master {user_master.first_name} has started a game.")

def join_game_callback(update, context):
    '''Command callback. When /joingame is called, it does the following:
    1. Checks if user has already joined the game
    1.1. If not, adds user who called it to the game's players list'''
    dixit_game = context.chat_data['dixit_game']
    user = update.message.from_user
    if user in dixit_game.get_user_list():
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=f"Damn you, {user.first_name}! You have already joined the game!")
    else:
        player = game.Player(user, hand_cards=[])
        dixit_game.add_player(player)
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=f"{user.first_name} was added to the game!")

def play_game_callback(update, context):
    '''Command callback. When /playgame is called, it does the following:
    1. Distributes cards to players;
    2. Chooses storyteller = 0 (the first player to join);
    3. (For later) Messages button to prompt inline query;
    4. Goes from stage 0 to 1.'''
    return

def inline_callback(update, context):
    '''Inline callback. It heavily depends on the stage of the game.'''
    if stage == 0:
        return
    elif stage == 1:
        return
    elif stage == 2:
        return
    elif stage == 3:
        return

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

    # Add commands handlers
    command_callbacks = {'startgame': start_game_callback,
                         'joingame': join_game_callback,
                         'playgame': play_game_callback}
    for name, callback in command_callbacks.items():
        dispatcher.add_handler(CommandHandler(name, callback))

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
