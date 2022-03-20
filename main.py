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

def get_active_games(context):
    '''Returns all `DixitGame`'s that are in `context.dispatcher.chat_data`
    as a dict of chat_id : dixit_game'''
    # There must be a better way of doing this...
    # In Haskell, I would have used `mapMaybe dixit_game chat_data` or smth
    if context.dispatcher.chat_data:
        dixit_game_dict = {chat_id : data['dixit_game']
                           for chat_id, data in context.dispatcher.chat_data.items()
                           if data.get('dixit_game', None)}
        return dixit_game_dict
    else:
        return {}

def find_user_games(context, user):
    '''Finds the `chat_id`'s of the games where the `user` is playing.
    Returns a dict of chat_id : dixit_game

    This is useful to resolve the issue of the inline queries not having
    the information about the chat from which it is requested.
    With the information of the `chat_id`'s, we could either prohibit the
    player from playing multiple games at once, or give him the choice of which
    game they want to play at that time like the unobot does.'''
    return {chat_id : dixit_game
            for chat_id, dixit_game in get_active_games(context).items()
            if user in dixit_game.get_user_list()}

def ensure_game(callback):
    """Decorator to ensure a game exists before callbacks are made"""
    def safe_callback(update, context):
        # Checks if there is an ongoing game
        user = update.message.from_user
        if 'dixit_game' not in context.chat_data.keys():
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text=f"Damn you, {user.first_name}! "
                                     "First, start a game with /startgame!")
        else:
            return callback(update, context)

    return safe_callback

def ensure_user_inactive(callback):
    """Decorator to ensure the user is not in another game"""
    def safe_callback(update, context):
        # Checks if there is an ongoing game
        user = update.message.from_user
        if find_user_games(context, user):
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text=f"Damn you, {user.first_name}! "
                                     "You are in another game already!")
        else:
            return callback(update, context)

    return safe_callback

@ensure_user_inactive
def start_game_callback(update, context):
    '''Command callback. When /startgame is called, it does the following:
    1. Checks if there is an ongoing game
    1.1. If not, creates a default DixitGame instance and stores it in
        context.chat_data (See more about this in
        https://github.com/python-telegram-bot/python-telegram-bot/wiki/Storing-bot,-user-and-chat-related-data#chat-migration,
        and about making it persistent in the future in
        https://github.com/python-telegram-bot/python-telegram-bot/wiki/Making-your-bot-persistent)
    2. Loads cards into game with random game_id's
    3. Sets this user as master
    4. Joins master user to the game IF they are not in other games
    '''
    user = update.message.from_user
    # Checks if there is no ongoing game
    if 'dixit_game' in context.chat_data.keys():
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=f"Damn you, {user.first_name}! "
                                       "There is a game in progress already!")
    else:
        game_id_list = list(range(1, 101))
        shuffle(game_id_list) # Permutates the game_id of the cards at random
        cards = [game.image_dixit_github(n, game_id_list[n-1])
                 for n in range(1, 101)]
        dixit_game = game.DixitGame(cards=cards)
        context.chat_data['dixit_game'] = dixit_game

        context.chat_data['master'] = user # Sets master
        master_player = game.Player(user)
        dixit_game.add_player(master_player)

        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text="Let's play Dixit!\n"
                                     f"The master {user.first_name} "
                                      "has started a game.")

@ensure_game
@ensure_user_inactive
def join_game_callback(update, context):
    '''Command callback. When /joingame is called, it does the following:
    1. Checks if user has already joined the game
    1.1. If not, adds user who called it to the game's players list'''
    dixit_game = context.chat_data['dixit_game']
    n_supported_players = len(dixit_game.cards)//dixit_game.cards_per_player
    user = update.message.from_user
    if user in dixit_game.get_user_list():
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=f"Damn you, {user.first_name}! "
                                       "You have already joined the game!")
    # Checks if there are enough cards for user to join
    elif len(dixit_game.players) >= n_supported_players:
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text="There are only enough cards in the"
                                     f"game to supply {n_supported_players} "
                                     "players, unfortunately!")
            # ask if they'd like to play with fewer cards per player?
    else:
        player = game.Player(user)
        dixit_game.add_player(player)
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=f"{user.first_name} was added to the game!"
                                 )

@ensure_game
def play_game_callback(update, context):
    '''Command callback. When /playgame is called, it does the following:
    1. Distributes cards to players;
    2. Chooses storyteller = 0 (the first player to join);
    3. (For later) Messages button to prompt inline query;
    4. Goes from stage 0 to 1.'''
    dixit_game = context.chat_data['dixit_game']
    master = context.chat_data['master']
    user = update.message.from_user
    # Checks if it was the master who requested /playgame
    if user != master:
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=f"Damn you, {user.first_name}! "
                                 "You are not the master {master.first_name}!")
    elif dixit_game.stage != 0:
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=f"Damn you, {user.first_name}! This is "
                                 "not the time to start playing the game!")
    else:
        # Distribute cards here
        dealer_cards = dixit_game.cards.copy()
        for player in dixit_game.players:
            for i in range(dixit_game.cards_per_player): # 6 cards per player
                card_index = randrange(len(dealer_cards))
                card = dealer_cards.pop(card_index)
                player.add_card(card)

        dixit_game.storyteller = 0 # por que não já deixar o valor padrão 0?
        dixit_game.next_stage()
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=f"The game has begun!")

def inline_callback(update, context):
    '''Inline callback. It depends on the stage of the game:
    If stage == 1 or 2, then show the player's cards
    If stage == 3, then show chosen cards
    Otherwise, do nothing'''
    user = update.inline_query.from_user
    dixit_game_dict = find_user_games(context, user)
    if len(dixit_game_dict) == 1:
        dixit_game = list(dixit_game_dict.values())[0]
        player_index = dixit_game.get_user_list().index(user)
        player = dixit_game.players[player_index]
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
        else:
            results = [] # gostaria de botar um texto, mas n vi como

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
        token = token_file.readline().strip() # Remove \n at the end
        run_bot(token)
