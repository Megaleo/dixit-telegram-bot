from telegram import Update, InlineQueryResultPhoto, InputTextMessageContent
from telegram.ext import (Updater, CallbackContext, CommandHandler,
                          InlineQueryHandler, MessageHandler, Filters)
from uuid import uuid4
import logging
import functools

from game import DixitGame

'''
TODO

[ ] End game: ask Master whether to end game or not

[ ] Improve the way results are shown; one of the fun parts of dixit is
    discussing whose answer each person has chosen

[ ] Force InlineQuery to discard its cache and update itself even on empty
    queries

[ ] Confirm that player's chosen cards were available for choosing, at every
    stage

[ ] Show user buttons to direct him to his cards automatically (vide Uno_Bot)

[ ] Have the bot reply to the relevant message, instead of sending simple
    messages, when appropriate

[ ] Have dummy players to better debug the game alone. They would not be
    storytellers, but could just always choose a random card when playing/voting.
'''

def send_message(text, update, context, **kwargs):
    '''Sends message to group chat specified in update and logs that'''
    context.bot.send_message(chat_id=update.effective_chat.id, text=text,
                             **kwargs)
    logging.debug(f'Sent message \"{text}\" to chat {update.effective_chat.id=}')


def send_photo(photo_url, update, context, **kwargs):
    '''Sends photo to group chat specified in update and logs that.'''
    context.bot.send_photo(chat_id=update.effective_chat.id, photo=photo_url,
                           **kwargs)
    logging.debug(f'Sent photo with url \"{photo_url}\" to chat {update.effective_chat.id=}')


def get_active_games(context):
    '''Returns all `DixitGame`'s that are in `context.dispatcher.chat_data`
    as a dict of chat_id: dixit_game'''
    if (chat_data := context.dispatcher.chat_data):
        active_games = {chat_id: data['dixit_game'] for chat_id, data in
                        chat_data.items() if 'dixit_game' in data}
        return active_games
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
            if user in dixit_game.users}


def ensure_game(exists=True):
    """Decorator to ensure a game exists before callbacks are made.
    Reverse if exists is False"""
    def ensure_game_decorator(callback):
        @functools.wraps(callback) # Preserve info about callback
        def safe_callback(update, context):
            # Checks if there is an ongoing game
            user = update.message.from_user
            if ('dixit_game' in context.chat_data.keys()) != exists:
                if exists:
                    send_message(f"Damn you, {user.first_name}! First, start a "
                                  "game with /startgame!", update, context)
                else:
                    send_message(f"Damn you, {user.first_name}! There is a game "
                                  "in progress already!", update, context)
            else:
                return callback(update, context)
        return safe_callback
    return ensure_game_decorator


def ensure_user_inactive(callback):
    """Decorator to ensure the user is not in another game"""
    @functools.wraps(callback) # Preserve info about callback
    def safe_callback(update, context):
        user = update.message.from_user
        if find_user_games(context, user):
            send_message(f"Damn you, {user.first_name}! You are in another "
                          "game already!", update, context)
        else:
            return callback(update, context)
    return safe_callback


@ensure_game(exists=False)
@ensure_user_inactive
def start_game_callback(update, context):
    '''Command callback. When /startgame is called, it does the following:
    1. Checks if there is an ongoing game
    1.1. If not, creates a default DixitGame instance and stores it in
        context.chat_data (See more about this in
        https://github.com/python-telegram-bot/python-telegram-bot/wiki/Storing-bot,-user-and-chat-related-data#chat-migration,
        and about making it persistent in the future in
        https://github.com/python-telegram-bot/python-telegram-bot/wiki/Making-your-bot-persistent)
    2. Loads cards into game with random _id's
    3. Sets this user as master
    4. Joins master user to the game IF they are not in other games
    '''
    user = update.message.from_user

    logging.info("GAME START")
    logging.info("We're now at stage 0: Lobby!")

    dixit_game = DixitGame.start_game(master=user)

    context.chat_data['dixit_game'] = dixit_game
    send_message(f"Let's play Dixit!\nThe master {dixit_game.master} "
                  "has started a game. Click /joingame to join and "
                  "/playgame to start playing!",
                  update, context)


@ensure_game(exists=True)
@ensure_user_inactive
def join_game_callback(update, context):
    '''Command callback. When /joingame is called, it does the following:
    1. Checks if user has already joined the game
    1.1. If not, adds user who called it to the game's players list'''
    dixit_game = context.chat_data['dixit_game']
    user = update.message.from_user
    if user in dixit_game.users:
        send_message(f"Damn you, {user.first_name}! You have already joined "
                      "the game!", update, context)
        return
    # Checks if there are enough cards for user to join
    if len(dixit_game.players) >= dixit_game.max_players:
        send_message("There are only enough cards in the game to supply "
                     f"{dixit_game.max_players} players, unfortunately!",
                     update, context)
        # ask if they'd like to play with fewer cards per player?
        return

    logging.info(f'{user.first_name=}, {user.id=} joined the game')
    dixit_game.add_player(user)
    send_message(f"{user.first_name} was added to the game!", update, context)


@ensure_game(exists=True)
def play_game_callback(update, context):
    '''Command callback. When /playgame is called, it does the following:
    1. Distributes cards to players;
    2. Chooses random storyteller
    3. (For later) Messages button to prompt inline query;
    4. Goes from stage 0 to 1.'''
    dixit_game = context.chat_data['dixit_game']
    user = update.message.from_user
    # Checks if it was the master who requested /playgame
    if user != dixit_game.master.user:
        send_message(f"Damn you, {user.first_name}! You are not the master "
                     f"{dixit_game.master}!", update, context)
        return
    # Check if the game hadn't been started before
    if dixit_game.stage != 0:
        send_message(f"Damn you, {user.first_name}! This is not the time to "
                     "start playing the game!", update, context)
        return

    send_message(f"The game has begun!", update, context)
    storytellers_turn(update, context)


def storytellers_turn(update, context):
    dixit_game = context.chat_data['dixit_game']
    logging.info("We're now at stage 1: Storyteller's turn!")

    dixit_game.play_game() # can no longer log the chosen cards!

    send_message(f'{dixit_game.storyteller} is the storyteller!\n'
                 'Please write a hint and click on a card.', update, context)


def inline_callback(update, context):
    '''Inline callback. It depends on the stage of the game:
    If stage == 1 or 2, then show the player's cards
    If stage == 3, then show chosen cards
    Otherwise, do nothing'''
    user = update.inline_query.from_user
    user_games = find_user_games(context, user)

    if len(user_games) != 1:
        return

    [dixit_game] = user_games.values()
    [player] = [p for p in dixit_game.players if p.user == user]
    storyteller = dixit_game.storyteller

    logging.info(f'Inline from {player!r}')
    logging.info(f'Player is{" not" * (player!=storyteller)} the storyteller')

    if dixit_game.stage == 1 and player == storyteller:
        given_clue = update.inline_query.query
        results = [InlineQueryResultPhoto(
                   id = str(uuid4()),
                   photo_url = card.url,
                   thumb_url = card.url,
                   title = f"Card {card.id} in the storyteller's hand",
                   input_message_content = InputTextMessageContent(
                       f'{user.id}:{card.id}\n' + given_clue)
                   )
                   for card in player.hand]
    elif dixit_game.stage == 2 and player != storyteller:
        results = [InlineQueryResultPhoto(
                   id = str(uuid4()),
                   photo_url = card.url,
                   thumb_url = card.url,
                   title = f"card {card.id} in the player's hand",
                   input_message_content = InputTextMessageContent(
                   f"{user.id}:{card.id}")
                   )
                   for card in player.hand]
    elif dixit_game.stage == 3 and player != storyteller:
        results = [InlineQueryResultPhoto(
                   id = str(uuid4()),
                   photo_url = card.url,
                   thumb_url = card.url,
                   title = f"chosen card {card.id}",
                   input_message_content = InputTextMessageContent(
                   f"{user.id}:{card.id}")
                   )
                   for card in dixit_game.table.values()]
    else:
        results = [InlineQueryResultPhoto(
                   id = str(uuid4()),
                   photo_url = card.url,
                   thumb_url = card.url,
                   title = f"Card {card.id} in the player's hand",
                   input_message_content = InputTextMessageContent(
                       f'{user.first_name} is impatient...')
                   )
                   for card in player.hand]

    update.inline_query.answer(results)


def end_of_round(update, context):
    dixit_game = context.chat_data['dixit_game']

    round_results = dixit_game.count_points()
    storyteller_card = dixit_game.table[dixit_game.storyteller]

    send_message(f'The correct answer was...', update, context)
    send_message(dixit_game.clue, update, context)
    send_photo(storyteller_card.url, update, context)
    results = '\n'.join([f'{player} got {points} '
                         f'point{"s" if points!=1 else ""}!'
                         for player, points in round_results.items()])
    send_message(results, update, context)

    dixit_game.new_round()
    storytellers_turn(update, context)


def parse_cards(update, context):
    '''parses the user messages looking for the played cards'''
    dixit_game = context.chat_data['dixit_game']
    user = update.message.from_user
    text = update.message.text

    data, *clue = text.split('\n', maxsplit=1)
    user_id, card_id = (int(i) for i in data.split(':'))
    logging.info(f'Parsing {user_id=}, {card_id=}, {user.first_name=}, '
                 f'{user.id=}')

    try:
        [player] = [p for p in dixit_game.players if p.id == user_id]
    except ValueError:
        send_message(f'You, {user.first_name}, are not playing the game!',
                     update, context)
        return

    try:
        [card_sent] = [c for c in dixit_game.cards if c.id == card_id]
    except ValueError:
        send_message(f"This card doesn't exist, {player}!", update, context)
        return

    if dixit_game.stage == 1:
        assert player == dixit_game.storyteller, "Player is not the storyteller"

        if len(clue) != 1:
            send_message(f'You forgot to give us a clue!', update, context)
            return
        [clue] = clue
        logging.info(f'{clue=}')
        logging.info("We're now at stage 2: others' turn!")

        dixit_game.storyteller_turn(card=card_sent, clue=clue)

        send_message(f"Now, let the others send their cards!", update, context)

    elif dixit_game.stage == 2:
        dixit_game.player_turns(player=player, card=card_sent)

        logging.info(f"There are ({len(dixit_game.table)}/"
                     f"{len(dixit_game.players)}) cards on the table!")
        if dixit_game.stage == 3:
            logging.info("We're now at stage 3: vote!")
            send_message(f"Time to vote!", update, context)

    elif dixit_game.stage == 3:
        try:
            [sender] = [p for p in dixit_game.players
                        if dixit_game.table[p]==card_sent]
        except:
            send_message('This card belongs to no one, {player}!')

        dixit_game.voting_turns(player=player, vote=sender)

        logging.info(f"I've received ({len(dixit_game.votes)}/"
                     f"{len(dixit_game.players) - 1}) votes")
        if len(dixit_game.votes) == len(dixit_game.players)-1:
            end_of_round(update, context)


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
