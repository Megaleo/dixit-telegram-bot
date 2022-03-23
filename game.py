# Stages
# A stage is defined by a period when the bot is waiting for user input
#
#          No   End? Yes
#      +-------  0  --> Show final results
#      |         ^
#      V         |
# 0 -> 1 -> 2 -> 3
#
# 0 - LOBBY: Players entering the game/viewing results
# 1 - STORYTELLER: Storyteller chooses a clue and a card.
# 2 - PLAYERS: Each player chooses their card. They go to the table 
# 3 - VOTE: Players other than the storyteller choose their option
#
# (Show results of the game with points to each one)


from typing import Optional, List, Mapping
from telegram import User
from collections import Counter
from random import shuffle, choice
from enum import IntEnum

'''
TODO

[ ] Discard pile of cards (?)

[ ] Use (Int?)Enums to represent the stages of the game

[ ] End game: restart variables, accumulate points, etc.

[ ] Move all DixitGame-related operations when a new stage is started currently
    in main.py to methods of the class itself (DixitGame.voting_turn(),
    DixitGame.storyteller_turn(), etc.)
    [X] start_game()
    [X] play_game()
    [X] storytellers_turn()
    [X] player_turns()
    [X] voting_turns()
    [X] count_points()
    [ ] others?

[ ] Store game history for future analysis?
'''


class Stage(IntEnum):
    LOBBY = 0
    STORYTELLER = 1
    PLAYERS = 2
    VOTE = 3 


class Card:
    def __init__(self, image_id: int, _id: int):
        '''image_id is the id of the card's image in Telegram's cache (or,
        temporarily, on the web)
        _id is used by the bot to know which card each player has chosen,
        and is randomized every game'''
        self.image_id = image_id
        self.id = _id

    def __eq__(self, other):
        return (self.image_id, self.id) == (other.image_id, other.id)

    def __repr__(self):
        return f'Card({self.image_id = }, {self.id = })'

    @property
    def url(self):
        return 'https://raw.githubusercontent.com/jminuscula/dixit-online/'\
               + f'master/cards/card_{self.image_id:0>5}.jpg'


class Player:
    def __init__(self, user: User, hand=None):
        '''user contains id and name. See
        https://python-telegram-bot.readthedocs.io/en/latest/telegram.user.html#telegram.User
        for more'''
        self.user = user
        self.hand = hand or []
        self.name = ' '.join(filter(bool, [user.first_name, user.last_name]))
        self.id = self.user.id

    def __repr__(self):
        return f'Player({self.name=}, {self.user.id=})'

    def __str__(self):
        return self.name

    def __eq__(self, other):
        # we could change self.user.id to self.id, so as to be able to compare
        # Players and Users, but it can get messy
        return self.user.id == other.user.id

    def __hash__(self):
        return self.id

    def add_card(self, card):
        self.hand.append(card)


class DixitGame:
    def __init__(self,
                 stage: Stage = Stage.LOBBY,
                 players: Optional[Player] = None,
                 master: Optional[Player] = None,
                 storyteller: Optional[Player] = None,
                 clue: List[str] = None,
                 cards: List[Card] = None,
                 table: Mapping[Player, Card] = None, # Players' played cards
                 votes: Mapping[Player, Player] = None, # Players' voted storytll
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
    def stage(self, val: Stage):
        if val not in Stage:
            raise ValueError(f'Valid stages are given by the Stage enum class')
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
        '''adds player to game. Makes it master if there wasn't one'''
        if isinstance(player, User):
            player = Player(player)
        self.players.append(player)
        self.master = self.master or player

    @classmethod
    def start_game(self, master):
        game_ids = list(range(1, 101))
        shuffle(game_ids)
        cards = [Card(n, id_) for n, id_ in enumerate(game_ids, start=1)]
        shuffle(cards)
        game = self(cards=cards)
        game.add_player(master) # first player automatically master
        return game
    
    def play_game(self):
        dealer_cards = self.dealer_cards
        for player in self.players:
            for _ in range(self.cards_per_player): # 6 cards per player
                card = dealer_cards.pop()
                player.add_card(card)

        self.storyteller = choice(self.players)
        self.stage = Stage.STORYTELLER
    
    def storyteller_turn(self, card, clue):
        self.clue = clue
        self.table[self.storyteller] = card
        self.stage = Stage.PLAYERS 

    def player_turns(self, player, card):
        # allows players to overwrite the card sent
        self.table[player] = card
        if len(self.table) == len(self.players):
            ## descomente para encher mesa até 6
            # for i in range(6 - len(self.table)):
            #     self.table[i] = self.dealer_cards.pop()
            self.stage = Stage.VOTE

    def voting_turns(self, player, vote):
        self.votes[player] = vote

    def count_points(self):
        '''Implements traditional Dixit point counting'''
        player_points = Counter(self.votes.values())
        storyteller = self.storyteller
        storytller_wins = len(self.votes) > player_points[storyteller] > 0
        player_points[storyteller] = 3 if storyteller_wins else 0
        for player, vote in self.votes.items():
            player_points[player] += (2 + storyteller_wins)*(vote == storyteller)
        return player_points



