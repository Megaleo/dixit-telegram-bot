from telegram import Update, InlineQueryResultPhoto, InputTextMessageContent
from telegram.ext import (Updater, CallbackContext, CommandHandler,
                          InlineQueryHandler, MessageHandler, Filters)
from uuid import uuid4
from random import choices, shuffle, randrange
import sys
import logging

import game

# Following tutorial in
# https://github.com/python-telegram-bot/python-telegram-bot-wiki/Extensions-%E2%80%93-Your-first-Bot

def get_active_games(context):
    '''Returns all `DixitGame`'s that are in `context.dispatcher.chat_data`
    as a dict of chat_id: dixit_game'''
    # There must be a better way of doing this...
    # In Haskell, I would have used `mapMaybe dixit_game chat_data` or smth
    if context.dispatcher.chat_data:
        dixit_game_dict = {chat_id: data['dixit_game'] for chat_id, data in 
                           context.dispatcher.chat_data.items()
                           if 'dixit_game' in data}
        return dixit_game_dict
    else:
        return {}


def find_user_games(context, user):
    '''Finds the `chat_id`'s of the games where the `user` is playing.
    Returns a dict of chat_id: dixit_game

    This is useful to resolve the issue of the inline queries not having
    the information about the chat from which it is requested.
    With the information of the `chat_id`'s, we could either prohibit the
    player from playing multiple games at once, or give him the choice of which
    game they want to play at that time like the unobot does.'''
    return {chat_id: dixit_game
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
    print("################## GAME START ######################")
    print("\n\nWe're now in stage 0: Lobby!\n")
    # Checks if there is no ongoing game
    if 'dixit_game' in context.chat_data:
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=f"Damn you, {user.first_name}! "
                                       "There is a game in progress already!")
    else:
        game_id_list = list(range(1, 101))
        shuffle(game_id_list) # Permutates the game_id of the cards at random
        cards = [game.image_dixit_github(n, game_id_list[n-1])
                 for n in range(1, 101)]
        shuffle(cards)
        dixit_game = game.DixitGame(cards=cards, 
                                    chat_id=update.effective_chat.id)
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
    print(f'Entrou: {user.first_name=}, {user.id=}')
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
    # Check if the game hadn't been started before
    elif dixit_game.stage != 0:
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=f"Damn you, {user.first_name}! This is "
                                 "not the time to start playing the game!")
    else:
        # Distribute cards here
        dealer_cards = dixit_game.dealer_cards
        for player in dixit_game.players:
            print(f'giving cards to {player.name}')
            for _ in range(dixit_game.cards_per_player): # 6 cards per player
                # card_index = randrange(len(dealer_cards))
                # card = dealer_cards.pop(card_index)
                # player.add_card(card)
                card = dealer_cards.pop()
                print(card.game_id)
                player.add_card(card)

        # dixit_game.storyteller = 0 # por que não já deixar o valor padrão 0?
        dixit_game.storyteller = randrange(len(dixit_game.players))
        dixit_game.next_stage()
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=f"The game has begun!")
        storytellers_turn(update, context)


def storytellers_turn(update, context):
    print("\n\nWe're now in stage 1: Storyteller's turn!\n")
    dixit_game = context.chat_data['dixit_game']
    assert dixit_game.stage == 1, "We're not in the storyteller's turn!"
    storyteller = dixit_game.players[dixit_game.storyteller]
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text=f'{storyteller.name} is the storyteller!\n'
                             'Please write a hint and click on a card.'
                             )


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
        storyteller = dixit_game.players[dixit_game.storyteller]
        print(f'Inline from {player_index=}, {user.id=}, {user.first_name=}')
        print(f'{player==storyteller = }')

        if dixit_game.stage==1 and player==storyteller:
            given_clue = update.inline_query.query
            results = [InlineQueryResultPhoto(
                       id = str(uuid4()),
                       photo_url = card.photo_id,
                       thumb_url = card.photo_id,
                       title = f"Card {card.game_id} in the storyteller's hand",
                       input_message_content = InputTextMessageContent(
                           f'{user.id}:{card.game_id}\n' + given_clue)
                       )
                       for card in player.hand_cards]

        elif dixit_game.stage==2 and player!=storyteller:
            results = [InlineQueryResultPhoto(
                       id = str(uuid4()),
                       photo_url = card.photo_id,
                       thumb_url = card.photo_id,
                       title = f"Card {card.game_id} in the player's hand",
                       input_message_content = InputTextMessageContent(
                       f"{user.id}:{card.game_id}")
                       )
                       for card in player.hand_cards]

        elif dixit_game.stage==3 and player!=storyteller:
            results = [InlineQueryResultPhoto(
                       id = str(uuid4()),
                       photo_url = card.photo_id,
                       thumb_url = card.photo_id,
                       title = f"Chosen card {card.game_id}",
                       input_message_content = InputTextMessageContent(
                       f"{user.id}:{card.game_id}"
                       ))
                       for card in dixit_game.table.values()]
        else:
            results = [] # gostaria de botar um texto, mas n vi como

        update.inline_query.answer(results)


def parse_cards(update, context):
    '''Parses the user messages looking for the played cards'''
    dixit_game = context.chat_data['dixit_game']
    user = update.message.from_user
    text = update.message.text

    data, *clue = text.split('\n', maxsplit=1)
    user_id, card_id = (int(i) for i in data.split(':'))
    print(f'Parsing {user_id=}, {card_id=}, {user.first_name=}, {user.id=}')

    card_sent = [c for c in dixit_game.cards if c.game_id == card_id][0]

    if dixit_game.stage == 1:
        dixit_game.storyteller_card = card_id
        if len(clue) != 1:
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text=f'You forgot to give us a clue!')
            return
        print(f'{clue[0]=}')
        dixit_game.clue = clue[0]
        dixit_game.table[user_id] = card_sent
        dixit_game.stage = 2
        print("\n\nWe're now in stage 2: others' turn!\n")
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=f"Now, let the others send their cards!")
        return

    if dixit_game.stage == 2:
        # allows players to overwrite the card sent
        # TODO: check that the card was indeed in the player's hand
        dixit_game.table[user_id] = card_sent
        print(f"There are ({len(dixit_game.table)}/"
              f"{len(dixit_game.players)}) cards on the table!")
        if len(dixit_game.table) == len(dixit_game.players):
            # dixit_game.next_stage()
            ##### descomente para enxer mesa até 6
            # for i in range(6 - len(dixit_game.table)):
            #     dixit_game.table[i] = dixit_game.dealer_cards.pop()
            dixit_game.stage = 3
            print("\n\nWe're now in stage 3: Vote!\n")
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text=f"Time to vote!")
        return

    if dixit_game.stage == 3:
        print(f"I've received ({len(dixit_game.table)}/"
              f"{len(dixit_game.players) - 1}) votes")
        dixit_game.votes[user_id] = card_sent
        if len(dixit_game.votes) == len(dixit_game.players)-1:
            end_of_round(update, context)
        return


def end_of_round(update, context):
    dixit_game = context.chat_data['dixit_game']
    round_results = count_points(dixit_game)

    storyteller = dixit_game.players[dixit_game.storyteller]
    storyteller_card = dixit_game.table[storyteller.user.id]

    context.bot.send_message(chat_id=update.effective_chat.id,
                             text=f'the correct answer was...')
    context.bot.send_photo(chat_id=update.effective_chat.id,
                           photo=storyteller_card.photo_id)
    results = '\n'.join([f'{player.name} got {points} '
                         f'point{"s" if points!=1 else ""}!'
                         for player, points in round_results.items()])
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text=results)
    #TODO: sum points, reset variables, etc.


def count_points(dixit_game):
    #TODO
    return dict.fromkeys(dixit_game.players, 1)


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

    # Add messages handler, to parse the card ids sent by the player
    pattern = r'^\d+:\d+(?:\n.*)?$'
    message_handler = MessageHandler(Filters.regex(pattern), parse_cards)
    # I don't know why, but Filter.via_bot() isn't letting it pass...
    dispatcher.add_handler(message_handler)

    # Start the bot
    updater.start_polling()

    updater.idle()


if __name__ == '__main__':
    logging_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(format=logging_format, level=logging.INFO)
    with open('token.txt', 'r') as token_file:
        token = token_file.readline().strip() # Remove \n at the end
        run_bot(token)
