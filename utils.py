from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram import InlineQueryResultPhoto, InputTextMessageContent
from uuid import uuid4
from functools import wraps
from exceptions import *
import logging

def send_message(text, update, context, button=None, **kwargs):
    '''Sends message to group chat specified in update and logs it. If the
    button argument is passed, show the users a button with the specified
    text, directing them to the current list of cards stored inline'''
    markup = None
    if button is not None:
        keyboard = [[InlineKeyboardButton(button,
                     switch_inline_query_current_chat='')]]
        markup = InlineKeyboardMarkup(keyboard)

    context.bot.send_message(chat_id=update.effective_chat.id, text=text,
                             reply_markup=markup, **kwargs)
    logging.debug(f'Sent message "{text}" to chat {update.effective_chat.id=}')


def send_photo(photo_url, update, context, **kwargs):
    '''Sends photo to group chat specified in update and logs that.'''
    context.bot.send_photo(chat_id=update.effective_chat.id, photo=photo_url,
                           **kwargs)
    logging.debug(f'Sent photo with url "{photo_url}" to chat '
                  '{update.effective_chat.id=}')


def get_active_games(context):
    '''Returns all `DixitGame`'s that are in `context.dispatcher.chat_data`
    as a dict of chat_id: dixit_game'''
    chat_data = context.dispatcher.chat_data
    if chat_data is not None:
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
        @wraps(callback) # Preserve info about callback
        def safe_callback(update, context):
            # Checks if there is an ongoing game
            user = update.message.from_user
            if ('dixit_game' in context.chat_data.keys()) != exists:
                if exists:
                    send_message(f"Damn you, {user.first_name}! First, create a "
                                  "new game with /newgame!", update, context)
                else:
                    send_message(f"Damn you, {user.first_name}! There's a game "
                                  "in progress already!", update, context)
            else:
                return callback(update, context)
        return safe_callback
    return ensure_game_decorator


def ensure_user_inactive(callback):
    """Decorator to ensure the user is not in another game"""
    @wraps(callback) # Preserve info about callback
    def safe_callback(update, context):
        user = update.message.from_user
        if find_user_games(context, user):
            send_message(f"Damn you, {user.first_name}! You are in another "
                          "game already!", update, context)
        else:
            return callback(update, context)
    return safe_callback


def menu_card(card, player, text=None, clue=None):
    text = text or f'{player.id}:{card.id}' + f'\n{clue}'*(clue is not None)
    return InlineQueryResultPhoto(
            id = str(uuid4()),
            photo_url = card.url,
            thumb_url = card.url,
            title = f"Card {card.id} in {player}'s hand",
            input_message_content = InputTextMessageContent(text)
            )


def handle_exceptions(*exceptions):
    def decorator(f):
        def msg_f(update, context, *args, **kwargs):
            subs = {'user': update.message.from_user,
                    'dixit_game': context.chat_data.get('dixit_game', None),
                    }
            try:
                return f(update, context, *args, **kwargs)
            except exceptions as e:
                text = str(e).format(**subs)
                send_message(text, update, context)
        return msg_f
    return decorator
