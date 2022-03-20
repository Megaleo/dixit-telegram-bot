# Stages
# A stage is defined by a period when the bot is waiting for user input
#
#          No        Yes
#      +------- End? --> Show final results
#      |         ^
#      V         |
# 0 -> 1 -> 2 -> 3
#
# 0 : Players entering the game
# (Cards are given inline to each player)
# 1 : Storyteller broadcasts the clue
# 2 : Each player chooses their card, including storyteller
# (Cards are shown)
# 3 : Players other than the storyteller choose their option
# (Show results of the game with points to each one)
#
# TODO:
# - Discard pile of cards

from typing import Optional
from telegram import User

class Card:

    def __init__(self, photo_id: int, game_id: int):
        '''photo_id is the id of the photo in Telegram's cache (or, temporarily, on the web)
        game_id is used by the bot to know which card each player has chosen'''
        self.photo_id = photo_id
        self.game_id = game_id

class Player:

    def __init__(self, user: User, hand_cards: list[Card] = []):
        '''user contains id and name. See
        https://python-telegram-bot.readthedocs.io/en/latest/telegram.user.html#telegram.User
        for more'''
        self.user = user
        self.hand_cards = hand_cards

class DixitGame:

    def __init__(self,
                 stage: int = 0,
                 players: list[Player] = [],
                 storyteller: Optional[int] = None,
                 clue: Optional[str] = None,
                 cards: list[Card] = []):
        '''storyteller should be an integer indicating the index of the player in
        tge list `players` that is the storyteller'''
        self.stage = stage
        self.players = players
        self.storyteller = storyteller
        self.clue = clue
        self.cards = cards
        self.verify()

    def verify(self):
        '''Verify consistency of its properties'''
        if self.stage not in [0, 1, 2, 3]:
            raise ValueError(f'Stage number {self.stage} should be between 0 and 3')
        if self.storyteller and \
           self.storyteller not in range(0, len(self.players)):
            raise ValueError('There is no player in index' \
            + f'{self.storyteller} (maximum is {len(self.players)-1})')

    def add_player(self, player: Player):
        self.players.append(player)

    def get_user_list(self):
        return [player.user for player in self.players]

    def next_stage(self):
        self.stage = (self.stage + 1) % 4
