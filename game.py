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

[ ] Abstract away from DixitGame a more general "CardGame" class
'''


class CardGame:
    '''A general class for simple card games. Depends on a Player class which
    must implement a list-like .hand attribute containing his cards'''
    def __init__(self, 
                 players = None, # [Player],
                 cards = None,
                 cards_per_player=3,
                 cards_per_turn=1,
                 cards_per_draw=1,
                 ):
        self.players = players or []
        self.cards = cards or []
        self.cards_per_player = cards_per_player
        self.cards_per_turn = cards_per_turn
        self.table = {}
        self._draw_pile = None
        self.discard_pile = []
        self.score = dict.fromkeys(self.players, 0)
    
    @property
    def draw_pile(self):
        if self._draw_pile is None:
            self._draw_pile = self.cards.copy()
            shuffle(self._draw_pile)
        return self._draw_pile

    @classmethod
    def shuffle(cls, sequence): # so as not to need to import from random
        shuffle(sequence)

    def move_card(self, card, player, destination, origin=None, 
                  remove_method=list.remove):
        origin = origin or player.hand
        if card not in origin:
            raise ValueError("Card not available!")

        if isinstance(destination, list): add_method = list.append
        elif isinstance(destination, set): add_method = set.add
        elif isinstance(destination, dict): 
            add_method = lambda dic, val: dic.__setitem__(player, val)

        remove_method(origin, card) 
        add_method(destination, card)        

    def play_card(self, card, player):
        self.move_card(card, player, self.table)

    def discard(self, card, player):
        self.move_card(card, player, self.discard_pile)
        
    def distribute_cards(self, strict=True):
        draw_pile = self.draw_pile
        print(f'{len(draw_pile)=}')
        print(f'{self.players=}')
        for player in self.players:
            print(f'giving cards to {player}')
            missing_cards = self.cards_per_player - len(player.hand)
            print(f'{missing_cards=}')
            if strict and missing_cards != self.cards_per_turn:
                raise ValueError('Player has wrong number of cards!')
            for _ in range(missing_cards):
                card = draw_pile.pop()
                print(f'{card=}')
                player.add_card(card)

    def start_game(self):
        self.distribute_cards(strict=False)


    def new_round(self):
        self.discard_pile.extend(self.table.values())

        if len(self.draw_pile) < len(self.players) * self.cards_per_turn:
            shuffle(self.discard_pile)
            self.draw_pile.extend(self.discard_pile)
            self.discard_pile.clear()

        self.distribute_cards(strict=True)

        self.table.clear()
        self.votes.clear()


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


class DixitGame(CardGame):
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

        super().__init__(
                 players = players, # [Player],
                 cards = cards,
                 cards_per_player = 6,
                 cards_per_turn = 1,
                 cards_per_draw = 1,
                 )

        self._stage = stage
        self._storyteller = storyteller
        self.master = master
        self.clue = clue
        self.votes = votes or {}

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
        super().start_game()
        self.storyteller = choice(self.players)
        self.stage = Stage.STORYTELLER
    
    def storyteller_turn(self, card, clue):
        self.clue = clue
        self.play_card(card, self.storyteller)
        self.stage = Stage.PLAYERS 

    def player_turns(self, player, card):
        self.play_card(card, player)
        if len(self.table) == len(self.players):
            ## descomente para encher mesa até 6
            # for i in range(6 - len(self.table)):
            #     self.table[i] = self.draw_pile.pop()
            self.stage = Stage.VOTE

    def voting_turns(self, player, vote):
        self.move_card(vote, player, origin=self.table, destination=self.votes,
                       remove_method=lambda *x: None)

    def count_points(self):
        '''Implements traditional Dixit point counting'''
        player_points = Counter(self.votes.values())
        storyteller = self.storyteller
        storyteller_wins = len(self.votes) > player_points[storyteller] > 0
        player_points[storyteller] = 3 if storyteller_wins else 0
        for player, vote in self.votes.items():
            player_points[player] += (2 + storyteller_wins)*(vote == storyteller)
        self.results = player_points
        return player_points

    def new_round(self):
        '''Resets variables to start a new round of dixit'''
        super().new_round()

        s_teller_i = self.players.index(self.storyteller)
        self.storyteller = self.players[(s_teller_i + 1) % len(self.players)]
        
        for player in self.players:
            self.score.setdefault(player, 0)
            self.score[player] += self.results.get(player, 0)

        self.results = None
        self.stage = Stage.STORYTELLER
