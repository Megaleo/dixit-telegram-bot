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

from typing import Optional, List, Mapping
from telegram import User

'''
TODO

[ ] Discard pile of cards (?)

[ ] Use (Int?)Enums to represent the stages of the game

[ ] End game: restart variables, accumulate points, etc.

[ ] Move all DixitGame-related operations when a new stage is started currently
    in main.py to methods of the class itself (DixitGame.voting_turn(),
    DixitGame.storyteller_turn(), etc.)

[ ] Store game history for future analysis?
'''



class Card:
    def __init__(self, photo_id: int, game_id: int):
        '''photo_id is the id of the photo in Telegram's cache (or,
        temporarily, on the web)
        game_id is used by the bot to know which card each player has chosen'''
        self.photo_id = photo_id
        self.game_id = game_id

    def __eq__(self, other):
        return self.photo_id == other.photo_id and self.game_id == other.game_id

    def __repr__(self):
        return f'Card({self.photo_id = }, {self.game_id = })'

def image_dixit_github(n: int, game_id: int):
    '''Fetches the n-th image from the github image repo and returns the
    associated Card class'''
    url_imagem = 'https://raw.githubusercontent.com/jminuscula/'\
                 + f'dixit-online/master/cards/card_{n:0>5}.jpg'
    return Card(url_imagem, game_id)


class Player:
    def __init__(self, user: User, hand_cards=None):
        '''user contains id and name. See
        https://python-telegram-bot.readthedocs.io/en/latest/telegram.user.html#telegram.User
        for more'''
        self.user = user
        self.hand_cards = hand_cards or []
        self.name = ' '.join(filter(bool, [user.first_name, user.last_name]))

    def __repr__(self):
        return f'Player({self.name=}, {self.user.id=})'

    def __str__(self):
        return self.name

    def __eq__(self, other):
        return self.user.id == other.user.id

    def __hash__(self):
        return self.user.id

    def add_card(self, card):
        self.hand_cards.append(card)


class DixitGame:

    def __init__(self,
                 stage: int = 0,
                 players: Optional[Player] = None,
                 master: Optional[Player] = None,
                 storyteller: Optional[Player] = None,
                 clue: List[str] = None,
                 cards: List[Card] = None,
                 table: Mapping[Player, Card] = None, # Players' played cards
                 votes: Mapping[Player, Card] = None, # Players' voted cards
                 ):
        self._stage = stage
        self.players = players or []
        self._storyteller = storyteller
        self.master = master
        self.clue = clue
        self.cards = cards or []
        self.table = table or {}
        self.votes = votes or {}
        self._dealer_cards = None
        self.cards_per_player = 6

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
    def storyteller(self):
        return self._storyteller

    @storyteller.setter
    def storyteller(self, player):
        if player not in self.players:
            raise ValueError(f"There's no such player in the game!")
        self._storyteller = player

    @property
    def max_players(self):
        return len(self.cards)//self.cards_per_player

    @property
    def dealer_cards(self):
        if self._dealer_cards is None:
            self._dealer_cards = self.cards.copy()
        return self._dealer_cards

    @property
    def users(self):
        return [player.user for player in self.players]

    def add_player(self, player):
        if isinstance(player, User):
            player = Player(player)
        self.players.append(player)
        self.master = self.master or player


    ## A SER DEPRECADOS
    # # usar self.get_user_list.index(user)?
    # def find_player_by_user(self, user):
    #     '''Finds player by user. If not, returns ValueError'''
    #     for index, player in enumerate(self.players):
    #         if player.user == user:
    #             return index
    #     raise ValueError('No player found by user')

    # # [u.id for u in self.players].index(id)? Será que de fato reimplementamos?
    # def find_player_by_id(self, user_id):
    #     '''Finds player by user_id. If not, returns ValueError'''
    #     for index, player in enumerate(self.players):
    #         if player.user.id == user_id:
    #             return index
    #     raise ValueError('No player found by id')

    # def next_stage(self):
    #     self.stage = (self.stage + 1) % 4
