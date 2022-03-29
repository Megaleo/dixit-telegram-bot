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

[?] Discard pile of cards (?)

[X] Use (Int?)Enums to represent the stages of the game

[X] End game: restart variables, accumulate points, etc.

[X] Move all DixitGame-related operations when a new stage is started currently
    in main.py to methods of the class itself (DixitGame.voting_turn(),
    DixitGame.storyteller_turn(), etc.)
    [X] start_game() (now new_game())
    [X] play_game() (now start_game())
    [X] storytellers_turn()
    [X] player_turns()
    [X] voting_turns()
    [X] point_counter()

[ ] Store game history for future analysis?

[/] Be forgiving to mistakes: allow players to overwrite the cards and choices
    they made (Cards can be overwritten so long a new stage hasn't been triggered)
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
        return f'Card({self.image_id=}, {self.id=})'

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
        return f'Player(name={self.name}, id_={self.id})'

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
        self._draw_pile = None
        self.cards_per_player = 6
        self.discard_pile = []
        self.score = dict.fromkeys(self.players, [0, 0])
        self.lobby = []

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
    def draw_pile(self):
        if self._draw_pile is None:
            self._draw_pile = self.cards.copy()
        return self._draw_pile

    @property
    def users(self):
        return [player.user for player in self.players]

    def add_player(self, player):
        '''adds player to game. Makes it master if there wasn't one'''
        if isinstance(player, User):
            player = Player(player)
        if self.stage == Stage.LOBBY:
            self.players.append(player)
        else:
            self.lobby.append(player)
        self.master = self.master or player

    def refill_hand(self, player, strict=False):
        '''makes player hold `self.cards_per_player` cards again'''
        n_cards = self.cards_per_player - len(player.hand)
        if strict and n_cards!=1:
            raise ValueError('Player should not be missing more than one card!')
        if n_cards < 0:
            raise ValueError('Player has too many cards!')
        for _ in range(n_cards):
            player.hand.append(self.draw_pile.pop())

    @classmethod
    def new_game(self, master):
        game_ids = list(range(1, 101))
        shuffle(game_ids)
        cards = [Card(n, id_) for n, id_ in enumerate(game_ids, start=1)]
        shuffle(cards)
        game = self(cards=cards)
        game.add_player(master) # first player automatically master
        return game

    def start_game(self):
        draw_pile = self.draw_pile
        for player in self.players:
            self.refill_hand(player)
        self.storyteller = choice(self.players)
        self.stage = Stage.STORYTELLER

    def storyteller_turn(self, card, clue):
        self.clue = clue
        self.table[self.storyteller] = card
        # self.storyteller.hand.remove(card) # its safe-ish to remove it later
        self.stage = Stage.PLAYERS

    def player_turns(self, player, card):
        self.table[player] = card
        if len(self.table) == len(self.players):
            ## descomente para encher mesa até 6
            # for i in range(6 - len(self.table)):
            #     self.table[i] = self.draw_pile.pop()
            for player, card in self.table.items():
                player.hand.remove(card)
            self.stage = Stage.VOTE

    def voting_turns(self, player, vote):
        self.votes[player] = vote

    def point_counter(self):
        '''Implements traditional Dixit point counting'''
        player_points = Counter(self.votes.values())
        storyteller = self.storyteller
        storyteller_wins = len(self.votes) > player_points[storyteller] > 0
        player_points[storyteller] = 3 if storyteller_wins else 0
        for player, vote in self.votes.items():
            player_points[player] += (2 + storyteller_wins)*(vote == storyteller)
        return player_points

    def count_points(self):
        round_points = self.point_counter()
        for player in self.players:
            self.score.setdefault(player, [0, 0])
            self.score[player][0] += round_points.get(player, 0)
            self.score[player][1] = round_points.get(player, 0)
        # sort players by score
        self.score = dict(sorted(self.score.items(), key=lambda x: x[1],
                                 reverse=True))
        self.stage = Stage.LOBBY

    def end_of_round(self):
        self.stage = Stage.LOBBY
        self.count_points()

    def new_round(self):
        '''Resets variables to start a new round of dixit'''
        self.discard_pile.extend(self.table.values())
        s_teller_i = self.players.index(self.storyteller)
        self.storyteller = self.players[(s_teller_i + 1) % len(self.players)]

        for user in self.lobby:
            self.add_player(user)
        self.lobby.clear()

        if len(self.draw_pile) < len(self.players): # if not enough cards
            shuffle(self.discard_pile)
            self.draw_pile.extend(self.discard_pile)
            self.discard_pile.clear()

        for player in self.players:
            self.refill_hand(player)

        self.results = None
        self.table.clear()
        self.votes.clear()
        self.stage = Stage.STORYTELLER
