from telegram import (InlineKeyboardButton, InlineKeyboardMarkup,
                      InlineQueryResultPhoto, InputTextMessageContent)
from telegram.error import TelegramError
from uuid import uuid4
from functools import wraps
from exceptions import *
from enum import IntEnum
from PIL import Image
from cairo import ImageSurface
from random import choice
import logging
import os
import gc

def send_message(text, update, context, button=None, **kwargs):
    '''Sends message to group chat specified in update and logs it. If the
    button argument is passed, shows the users a button with the specified
    text, directing them to the current list of cards stored inline.
    '''
    markup = kwargs.pop('reply_markup', None)
    if button is not None:
        keyboard = [[InlineKeyboardButton(button,
                     switch_inline_query_current_chat='')]]
        markup = InlineKeyboardMarkup(keyboard)

    chat_id = get_chat_id(context)
    context.bot.send_message(chat_id=chat_id, text=text, reply_markup=markup,
                             **kwargs)
    logging.debug(f'Sent message "{text}" to chat {chat_id=}')


def send_photo(photo, update, context, **kwargs):
    '''Sends photo to group chat specified in update and logs it.'''
    chat_id = get_chat_id(context)
    context.bot.send_photo(chat_id=chat_id, photo=photo, **kwargs)
    if isinstance(photo, str):
        logging.debug(f'Sent photo "{photo}" to chat {chat_id=}')
    else:
        logging.debug(f'Sent photo to chat {chat_id=}')


def get_active_games(context):
    '''Returns all `DixitGame`'s stored in `context.dispatcher.chat_data`
    as a {chat_id: dixit_game} dict.
    '''
    chat_data = context.dispatcher.chat_data
    if chat_data is not None:
        active_games = {chat_id: data['dixit_game'] for chat_id, data in
                        chat_data.items() if 'dixit_game' in data}
        return active_games
    else:
        return {}


def find_user_games(context, user):
    '''Finds the `chat_id`'s of the games where the `user` is playing.
    Returns a {chat_id: dixit_game} dict.
    '''
    return {chat_id: dixit_game
            for chat_id, dixit_game in get_active_games(context).items()
            if user in dixit_game.users}


def get_game(context):
    """Retrieves the current chat from user_data"""
    chat_id = get_chat_id(context)
    data = context.dispatcher.chat_data[chat_id]
    return data['dixit_game']


def set_game(context):
    """Stores current chat ID in `user_data` and sets it as 'current chat'.
    """
    chat_id = get_chat_id(context)
    context.user_data.setdefault('games', []).append(chat_id)
    context.user_data['current chat'] = chat_id


def get_chat_id(context):
    try:
        chat_id = context.user_data['current chat']
    except KeyError:
        chat_id, _ = context._chat_id_and_data
    return chat_id


def ensure_game(exists=True):
    '''Decorator to ensure a game exists before callbacks are made.
    Ensures the opposite if `exists= False`
    '''
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
    '''Decorator to ensure the user is not in another game'''
    @wraps(callback) # Preserve info about callback
    def safe_callback(update, context):
        user = update.message.from_user
        if find_user_games(context, user):
            send_message(f"Damn you, {user.first_name}! You are in another "
                          "game already!", update, context)
        else:
            return callback(update, context)
    return safe_callback


def menu_card(card, player, text='🎴', clue=None):
    '''Returns the specified card as an InlineQueryResultPhoto menu item'''
    if clue is not None:
        text += '\n' + clue
    return InlineQueryResultPhoto(
            id = card.id, # str(uuid4()) + ':' + str(card.id),
            photo_url = card.url,
            thumb_url = card.url,
            title = f"Card {card.id} in {player}'s hand",
            input_message_content = InputTextMessageContent(text)
            )


def random_card_id(player, card_list):
    '''Returns message with a random chosen card from card_list'''
    card_id = choice(card_list).id
    return card_id


def random_card_from_hand(player):
    return random_card_id(player, player.hand)


def handle_exceptions(*exceptions):
    '''Decorator that catches the listed exception and forwards their text
    content to the chat specified in `context`.
    '''
    def decorator(f):
        def msg_f(update, context, *args, **kwargs):
            user = update.effective_user
            dixit_game = get_game(context)
            try:
                player = dixit_game.get_player_by_id(user.id)
            except (AttributeError, UserNotPlayingError):
                # dixit_game não definido OU player não existe
                player = None

            subs = {'user': user,
                    'dixit_game': dixit_game,
                    'player': player}
            try:
                return f(update, context, *args, **kwargs)
            except exceptions as e:
                text = str(e).format(**subs)
                send_message(text, update, context)
        return msg_f
    return decorator


def convert_jpg_to_png(filename_jpg, delete_jpg=False):
    if not filename_jpg.endswith('.jpg'):
        raise ValueError(f'{filename_jpg} does not end with .jpg')
    file_jpg = Image.open(filename_jpg)
    filename_png = f'{filename_jpg[:-4]}.png'
    file_jpg.save(filename_png)
    if delete_jpg:
        os.remove(filename_jpg)
    return filename_png

# Load card images into memory.
def load_cards():
    card_images = {}
    for card_file in os.listdir('assets/cards/png/'):
        image = open(f'assets/cards/png/{card_file}', 'rb')
        cairo_surface = ImageSurface.create_from_png(image)
        card_images[int(card_file[5:-4])] = image
    assert len(card_images) == 372
    return card_images
gc.collect()
class TelegramPhotoSize(IntEnum):
    # The sizes are from my experience. Don't trust this
    SMALL = 0 # 160x160
    MEDIUM = 1 # 320x320
    LARGE = 2 # 640x640
    XLARGE = 3 # > 640x640


def get_profile_pic(bot, user_id, size):
    '''Gets first profile pic of user of the chosen size and saves it in tmp/
    with name "pic_{user_id}.png". Returns the filename of image if successful
    and False if not.'''
    # TODO: What happens when user doesn't have a profile pic?
    try:
        user_profile_photos = bot.get_user_profile_photos(user_id, limit=1)
    except TelegramError as e:
        logging.warning(f'Could not get profile photo of user with id {user_id}.'
                        f'TelegramError raised with message: {str(e)}')
        return False
    # The photos come in batches of different sizes. Since I asked limit=1, then
    # only versions of the main photo (or first photo?) of the user are returned
    # in the list user_profile_photos.photos[0]
    # From my experience, telegram returns at least three sizes:
    # 160x160, 320x320 and 640x640.
    if not user_profile_photos.photos or not user_profile_photos.photos[0]:
        logging.warning(f'Could not get profile photo of user with id {user_id}.'
                        'user_profile_photos[0] does not exist or is empty')
        return False
    photo = user_profile_photos.photos[0][int(size)]
    logging.debug(f'Got photo of user with id {user_id} with size '
                  f'{photo.width}x{photo.height}')
    try:
        photo_file = photo.get_file()
    except TelegramError as e:
        logging.warning(f'Could not get profile photo of user with id {user_id}.'
                        f'TelegramError raised with message: {str(e)}')
        return False

    if not os.path.isdir('tmp'):
        os.makedirs('tmp')

    filename_jpg = f'tmp/pic_{user_id}.jpg'
    photo_file.download(custom_path=filename_jpg)
    filename_png = convert_jpg_to_png(filename_jpg, delete_jpg=True)
    return filename_png

def markdown_escape(string):
    '''Escapes forbidden symbols when using markdown'''
    symbols_to_escape = '_*[]()~`>#+-=|{}.!'
    escaped_string = string
    for symbol in symbols_to_escape:
        escaped_string =  escaped_string.replace(symbol, '\\'+symbol)
    return escaped_string

