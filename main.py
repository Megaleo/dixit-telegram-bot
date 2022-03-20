from telegram import Update, InlineQueryResultPhoto, InputTextMessageContent
from telegram.ext import (Updater, CallbackContext, CommandHandler,
                          InlineQueryHandler)
from uuid import uuid4
from random import choices, shuffle, randrange
import sys
import logging

import game

# Following tutorial in
# https://github.com/python-telegram-bot/python-telegram-bot-wiki/Extensions-%E2%80%93-Your-first-Bot


def start_game_callback(update, context):
    '''Command callback. When /startgame is called, it does the following:
    1. Checks if there is an ongoing game
    1.1. If not, creates a default DixitGame instance and stores it in context.chat_data
    (See more about this in https://github.com/python-telegram-bot/python-telegram-bot/wiki/Storing-bot,-user-and-chat-related-data#chat-migration ,
    and about making it persistent in the future in https://github.com/python-telegram-bot/python-telegram-bot/wiki/Making-your-bot-persistent )
    2. Loads cards into game with random game_id's
    3. Sets this user as master
    4. Joins master user to the game
    '''
    user = update.message.from_user
    # Checks if there is no ongonig game
    if 'dixit_game' in context.chat_data.keys():
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=f"Damn you, {user.first_name}! There is a game in progress!")
    else:
        game_id_list = list(range(1, 101))
        shuffle(game_id_list) # Permutates the game_id of the cards at random
        cards = [game.image_dixit_github(n, game_id_list[n-1]) for n in range(1, 101)]
        dixit_game = game.DixitGame(cards = cards)
        context.chat_data['dixit_game'] = dixit_game

        context.chat_data['master'] = user # Sets master
        master_player = game.Player(user, hand_cards=[])
        dixit_game.add_player(master_player)

        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text="Let's play Dixit!\n"\
                                 + f"The master {user.first_name} has started a game.")

def join_game_callback(update, context):
    '''Command callback. When /joingame is called, it does the following:
    1. Checks if user has already joined the game
    1.1. If not, adds user who called it to the game's players list'''
    user = update.message.from_user
    # Checks if there is a game
    if 'dixit_game' not in context.chat_data.keys():
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=f"Damn you, {user.first_name}! First, start a game with /startgame!")
    else:
        dixit_game = context.chat_data['dixit_game']
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
    user = update.message.from_user
    # Checks if there is a game
    if 'dixit_game' not in context.chat_data.keys():
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=f"Damn you, {user.first_name}! First, start a game with /startgame!")
    else:
        dixit_game = context.chat_data['dixit_game']
        master = context.chat_data['master']
        # Checks if it was the master who requested /playgame
        if user != master:
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text=f"Damn you, {user.first_name}! You are not the master {master.first_name}!")
        elif dixit_game.stage != 0:
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text=f"Damn you, {user.first_name}! This is not the time to start playing the game!")
        else:
            # Distribute cards here
            cpp = dixit_game.cards_per_player
            if len(dixit_game.players) * cpp > len(dixit_game.cards):
                context.bot.send_message(chat_id=update.effective_chat.id,
                                         text=f"Not enough cards!")
            else:
                dealer_cards = dixit_game.cards.copy()
                for player in dixit_game.players:
                    for i in range(cpp): # 6 cards per player
                        card_index = randrange(len(dealer_cards))
                        player.add_card(dealer_cards[card_index])
                        del dealer_cards[card_index]

                dixit_game.storyteller = 0
                dixit_game.next_stage()
                context.bot.send_message(chat_id=update.effective_chat.id,
                                         text=f"The game has begun!")

def inline_callback(update, context):
    '''Inline callback. It depends on the stage of the game:
    If stage == 1 or 2, then show the player's cards
    If stage == 3, then show chosen cards
    Otherwise, do nothing'''
    user = update.inline_query.from_user
    if 'dixit_game' in context.chat_data.keys():
        dixit_game = context.chat_data['dixit_game']
        if user in dixit_game.get_user_list():
            player = dixit_game.find_player_by_user(user)
            if dixit_game.stage in [1, 2]:
                results = [InlineQueryResultPhoto(
                           id = str(uuid4()),
                           photo_url = card.photo_id,
                           thumb_url = card.photo_id,
                           title = f"Card {card.game_id} in the player's hand",
                           input_message_content = InputTextMessageContent(
                           f"{user.id}:{card.game_id}"
                           ))
                           for card in player.hand_cards]
            elif dixit_game.stage == 3:
                results = [InlineQueryResultPhoto(
                           id = str(uuid4()),
                           photo_url = card.photo_id,
                           thumb_url = card.photo_id,
                           title = f"Chosen card {card.game_id}",
                           input_message_content = InputTextMessageContent(
                           f"{user.id}:{card.game_id}"
                           ))
                           for card in dixit_game.chosen_cards]

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
    updater = Updater(token, use_context=True)
    dispatcher = updater.dispatcher

    # Add commands handlers
    command_callbacks = {'startgame': start_game_callback,
                         'joingame': join_game_callback,
                         'playgame': play_game_callback}
    for name, callback in command_callbacks.items():
        dispatcher.add_handler(CommandHandler(name, callback))

    # Add inline handler
    inline_handler = InlineQueryHandler(inline_callback)
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
