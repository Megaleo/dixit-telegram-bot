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

from typing import Optional, List
from telegram import User

class Card:

    def __init__(self, photo_id: int, game_id: int):
        '''photo_id is the id of the photo in Telegram's cache (or,
        temporarily, on the web)
        game_id is used by the bot to know which card each player has chosen'''
        self.photo_id = photo_id
        self.game_id = game_id

    def __eq__(self, other):
        return self.photo_id == other.photo_id and self.game_id == other.game_id


def image_dixit_github(n: int, game_id: int):
    '''Fetches the n-th image from the github image repo and returns the
    associated Card class'''
    url_imagem = 'https://raw.githubusercontent.com/jminuscula/'\
                 + f'dixit-online/master/cards/card_{n:0>5}.jpg'
    return Card(url_imagem, game_id)


class Player:

    def __init__(self, user: User, hand_cards = []):
        '''user contains id and name. See
        https://python-telegram-bot.readthedocs.io/en/latest/telegram.user.html#telegram.User
        for more'''
        self.user = user
        self.hand_cards = hand_cards

    def add_card(self, card):
        self.hand_cards.append(card)


class DixitGame:

    def __init__(self,
                 stage: int = 0,
                 players: List[Player] = [],
                 storyteller: Optional[int] = None,
                 clue: Optional[str] = None,
                 cards: List[Card] = [],
                 chosen_cards: List[int] = [], # list of game_id's
                 storyteller_card: Optional[int] = None, # game_id of card
                 cards_per_player: int = 6):
        '''storyteller should be an integer indicating the index of the player
        in the list 'players' that is the storyteller'''
        self.stage = stage
        self.players = players
        self.storyteller = storyteller
        self.clue = clue
        self.cards = cards
        self.cards_per_player = cards_per_player
        # self.verify()

    # ESTOU COMENTANDO ISSO EM FAVOR DA ABORDAGEM COM SETTERS ABAIXO
    # MAS TALVEZ DEVESSEMOS SÓ USAR ENUMS?
    #
    # def verify(self):
    #     '''Verify consistency of its properties'''
    #     if self.stage not in [0, 1, 2, 3]:
    #         raise ValueError(f'Stage number {self.stage} '
    #                           'should be between 0 and 3')
    #     if self.storyteller and 
    #        self.storyteller not in range(len(self.players)):
    #         raise ValueError(f'There is no player in index {self.storyteller} '
    #                          f'(maximum is {len(self.players)-1})')
    
    @property
    def stage(self):
        return self._stage

    @stage.setter
    def stage(self, val: int):
        if val not in range(4):
            raise ValueError(f'Stage number {self.stage} '
                              'should be between 0 and 3 (inclusive)')
        self._stage = val


    @property
    def storyteller(self, val: int):
        return self._storyteller

    @storyteller.setter
    def storyteller(self, val: int):
        if val is not None and val not in range(len(self.players)):
            raise ValueError(f'There is no player in index {self.storyteller} '
                             f'(maximum is {len(self.players)-1})')
        self._storyteller = val
    

    def add_player(self, player: Player):
        self.players.append(player)

    def get_user_list(self):
        return [player.user for player in self.players]

    # usar self.get_user_list.index(user)?
    def find_player_by_user(self, user):
        '''Finds player by user. If not, returns ValueError'''
        for index, player in enumerate(self.players):
            if player.user == user:
                return index
        raise ValueError('No player found by user')

    # [u.id for u in self.players].index(id)? Será que de fato reimplementamos?
    def find_player_by_id(self, user_id):
        '''Finds player by user_id. If not, returns ValueError'''
        for index, player in enumerate(self.players):
            if player.user.id == user_id:
                return index
        raise ValueError('No player found by id')

    def next_stage(self):
        self.stage = (self.stage + 1) % 4
