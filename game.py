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


from typing import Optional, List, Mapping, Tuple
from telegram import User
from collections import Counter
from random import shuffle, choice, sample
from enum import Enum, IntEnum
from exceptions import *
from dataclasses import dataclass
from uuid import uuid4, UUID
import copy


class Stage(IntEnum):
    LOBBY = 0
    STORYTELLER = 1
    PLAYERS = 2
    VOTE = 3


class EndCriterion(Enum):
    LAST_CARD = 0
    POINTS = 1
    ROUNDS = 2
    ENDLESS = 3


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
        return f'https://play-dixit.online/cards/card_{self.image_id}.jpg'


class Player:
    def __init__(self, user: User, hand=None):
        '''Represents a player taking part in the game'''
        self.user = user
        self.hand = hand or []
        self.first_name = user.first_name
        self.last_name = user.last_name
        self.username = user.username
        self.id = self.user.id

    def __repr__(self):
        return f'Player(name={self.name}, id_={self.id})'

    def __str__(self):
        return self.__format__('full')

    def __eq__(self, other):
        # we could change self.user.id to self.id, so as to be able to compare
        # Players and Users, but it can get messy
        if not isinstance(other, Player):
            return False
        return self.user.id == other.user.id

    def __hash__(self):
        return self.id

    def __format__(self, spec='full'):
        '''spec has the general form [@][format]['s], meaning:
        @      - Mention the user by id, (off by default)
        format - The name format. One of [full (default), formal, first]
        's     - Use the possessive form of the name (off by default)
        '''
        # if the spec gets more complex, consider using regex
        form = spec.removeprefix('@').removesuffix("'s")
        mention = spec.startswith('@')
        possessive = spec.endswith("'s")

        if form == 'full':
            name = ' '.join(filter(bool, [self.first_name, self.last_name]))
        elif form == 'formal':
            if self.last_name:
                name =  self.first_name[0] + '. ' + self.last_name
            else:
                name = self.first_name
        elif form == 'first':
            name = self.first_name
        elif form == '':
            name = self.__format__()
        else:
            raise ValueError(f'Unsupported format spec: {spec!r}')

        name += ("'" if name.endswith('s') else "'s")*possessive
        name = f'[{name}](tg://user?id={self.id})' if mention else name
        return name

    @property
    def name(self):
        return self.__format__('full')

    def add_card(self, card):
        self.hand.append(card)


@dataclass(frozen=True)
class DixitResults:
    '''Represent results of a round of Dixit.
    It has:
    - List with all players;
    - Who is the storyteller;
    - Who voted whom;
    - Who player which card;
    - What was the clue;
    - Total points after the round and new points compared to the previous.
    '''
    game_id: UUID
    game_number: int
    round_number: int
    players: List[Player]
    storyteller: Player
    votes: Mapping[Player, Player]
    table: Mapping[Player, Card]
    clue: str
    score: Mapping[Player, int]
    delta_score: Mapping[Player, int]


class DixitGame:
    '''The main class. Handles the game logic'''
    def __init__(self,
                 stage: Stage = Stage.LOBBY,
                 players: Optional[Player] = None,
                 master: Optional[Player] = None,
                 storyteller: Optional[Player] = None,
                 clue: Optional[str] = None,
                 cards: List[Card] = None,
                 table: Mapping[Player, Card] = None, # Players' played cards
                 votes: Mapping[Player, Player] = None, # Players' voted storytll
                 end_criterion = EndCriterion.LAST_CARD,
                 end_criterion_number = None,
                 game_id = None
                 ):
        self._stage = stage
        self.players = players or []
        self._storyteller = storyteller
        self.master = master
        self.clue = clue
        self.table = table or {}
        self.votes = votes or {}
        self.end_criterion = end_criterion
        self.end_criterion_number = end_criterion_number
        self._draw_pile = None
        self.cards_per_player = 6
        self.discard_pile = []
        self.score = dict.fromkeys(self.players, 0)
        self.delta_score = dict.fromkeys(self.players, 0)
        self.lobby = []
        self.round_number = 1
        self.game_number = 1
        self.game_id = game_id or uuid4()

        if cards is None:
            game_ids = list(range(1, 373))
            shuffle(game_ids)
            cards = [Card(n, id_) for n, id_ in enumerate(game_ids, start=1)]
            shuffle(cards)
            self.cards = cards

        if self.master is None and self.players:
            self.master = self.players[0]
        if isinstance(self.master, User):
            self.master = Player(self.master)
        if self.master is not None and self.master not in self.players:
            self.players.append(self.master)

    end_criteria = EndCriterion

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

    def has_ended(self):
        if self.end_criterion == EndCriterion.LAST_CARD:
            return len(self.cards) < len(self.players) * self.cards_per_player
        elif self.end_criterion == EndCriterion.POINTS:
            return max(self.score.values()) >= self.end_criterion_number
        elif self.end_criterion == EndCriterion.ROUNDS:
            return self.round_number >= self.end_criterion_number

    def add_player(self, player):
        '''Adds player to game. Makes it master if there wasn't one.
        Returns:
            1 if the player was added to the lobby because of voting stage
            2 if the player was added to the lobby because of not enough cards
            3 if the player was added to the players list'''
        player = Player(player) if isinstance(player, User) else player

        if player in self.players:
            raise UserAlreadyInGameError("Damn you, {user.first_name}! You have "
                   "already joined the game!")

        if len(self.players) >= self.max_players:
           raise TooManyPlayersError("{user.first_name} Can't join the game! "
                   "There are only enough cards to supply "
                   "{dixit_game.max_players} players, unfortunately!")

        self.master = self.master or player
        if self.stage == Stage.VOTE:
            self.lobby.append(player)
            return 1
        elif self.stage == Stage.STORYTELLER or self.stage == Stage.PLAYERS:
            if len(self.draw_pile) < self.cards_per_player:
                self.lobby.append(player)
                return 2
            else:
                self.players.append(player)
                self.refill_hand(player)
                return 3
        elif self.stage == Stage.LOBBY:
            self.players.append(player)
            return 3

    def refill_hand(self, player, strict=False):
        '''Makes player hold `self.cards_per_player` cards again'''
        n_cards = self.cards_per_player - len(player.hand)
        if strict and n_cards!=1:
            raise HandError('Player should not be missing more than one card!')
        if n_cards < 0:
            raise HandError('Player has too many cards!')

        for _ in range(n_cards):
            player.hand.append(self.draw_pile.pop())

    def start_game(self, master):
        '''Makes draw pile, deals cards, chooses storyteller, starts the game'''
        if master != self.master.user:
            raise UserIsNotMasterError("Damn you, {user.first_name}! "
                    "You are not the master {dixit_game.master}!")
        if self.stage != Stage.LOBBY:
            raise GameAlreadyStartedError("Damn you, {user.first_name}! "
                    "The game has started already!")
        for player in self.players:
            self.refill_hand(player)
        self.storyteller = choice(self.players)
        self.stage = Stage.STORYTELLER

    def get_player_by_id(self, player_id):
        try:
            [player] = [p for p in self.players if p.id == player_id]
        except ValueError:
            raise UserNotPlayingError('You, {user.first_name}, are not playing '
                                      'the game!')
        return player

    def get_card_by_id(self, card_id):
        try:
            [card] = [c for c in self.cards if c.id == card_id]
        except ValueError:
            raise CardDoesntExistError("This card doesn't exist, {player}!")
        return card

    def storyteller_turn(self, player, card, clue):
        '''Stores the given clue and card, advances stage'''
        if player != self.storyteller:
            raise PlayerNotStorytellerError('{player} is not the storyteller!')
        if not clue:
            raise ClueNotGivenError('You forgot to give us a clue!\n\n'
                                    ' •  Click the button above to see your '
                                    'cards\n'
                                    ' •  Write your clue\n'
                                    ' •  Choose your card and send it along '
                                    'with the clue!')
        self.clue = clue
        self.table[self.storyteller] = card
        self.stage = Stage.PLAYERS

    def player_turns(self, player, card):
        '''Stores player cards, advances stage when all have played'''
        if player == self.storyteller:
            raise PlayerIsStorytellerError("As the Storyteller, you have already "
                                           "chosen your card and clue, {player}!")
        self.table[player] = card
        if len(self.table) == len(self.players):
            for player, card in self.table.items():
                player.hand.remove(card)
            # shuffling the table (using shuffle() is more complicated)
            self.table = dict(sample(self.table.items(), k=len(self.table)))
            self.stage = Stage.VOTE

    def voting_turns(self, player, card):
        '''Gets card voted by each player and stores its sender in the `votes`
        dict. Ends round when all have voted.
        '''
        try:
            [sender] = [p for p in self.players if self.table[p] == card]
        except ValueError:
            raise CardHasNoSenderError('This card belongs to no one, {player}!')
        if sender == player:
            raise VotingError("You can't vote for your own card, {player}!")
        if player == self.storyteller:
            raise PlayerIsStorytellerError("The Storyteller can't vote, "
                                           "{player}!")
        self.votes[player] = sender
        if len(self.votes) == len(self.players)-1:
            self.end_of_round()

    def end_of_round(self):
        '''End of round tasks: Advance the stage and count the points'''
        self.stage = Stage.LOBBY
        self.point_counter()
        self.count_points()

    def get_results(self) -> DixitResults:
        '''Returns (a deepcopy of) the results in an instance of DixitResults'''
        results = DixitResults(game_id = self.game_id,
                               game_number = self.game_number,
                               round_number = self.round_number,
                               players = self.players,
                               storyteller = self.storyteller,
                               votes = self.votes,
                               table = self.table,
                               clue = self.clue,
                               score = self.score,
                               delta_score = self.delta_score
                               )
        return results

    def point_counter(self):
        '''Implements traditional Dixit point-counting'''
        player_points = Counter(self.votes.values())
        storyteller = self.storyteller
        good_hint = len(self.votes) > player_points[storyteller] > 0
        player_points[storyteller] = 3 if good_hint else 0
        for player, vote in self.votes.items():
            player_points[player] += 3*(vote==storyteller) if good_hint else 2
        for player in self.players:
            self.delta_score[player] = player_points.get(player, 0)

    def count_points(self):
        '''Adds delta_score to score, sorts it and goes to LOBBY phase'''
        for player in self.players:
            self.score.setdefault(player, 0)
            self.score[player] += self.delta_score.get(player, 0)
        # sort players by score
        self.score = dict(sorted(self.score.items(), key=lambda x: x[1],
                                 reverse=True))
        self.stage = Stage.LOBBY

    def housekeeping(self):
        '''Shared variable operations at the end of round and game'''
        s_teller_i = self.players.index(self.storyteller)
        self.storyteller = self.players[(s_teller_i + 1) % len(self.players)]

        for user in self.lobby:
            assert self.add_player(user) == 3
        self.lobby.clear()

        self.clue = None
        self.table.clear()
        self.votes.clear()
        self.stage = Stage.STORYTELLER

    def new_round(self):
        '''Resets variables to start a new round of dixit'''
        self.discard_pile.extend(self.table.values())
        self.housekeeping()

        n_cards_to_be_added = 0
        for player in self.players:
            n_cards_to_be_added += self.cards_per_player - len(player.hand)
        if len(self.draw_pile) < n_cards_to_be_added: # if not enough cards
            shuffle(self.discard_pile)
            self.draw_pile.extend(self.discard_pile)
            self.discard_pile.clear()

        for player in self.players:
            self.refill_hand(player)
        self.round_number += 1

    def restart_game(self):
        '''Resets variables to restart the game of dixit'''
        self.housekeeping()
        game_ids = list(range(1, 101))
        shuffle(game_ids)
        cards = [Card(n, id_) for n, id_ in enumerate(game_ids, start=1)]
        shuffle(cards)
        self.cards = cards
        self._draw_pile = self.cards.copy()
        self.score = dict.fromkeys(self.players, 0)
        self.round_number = 1
        self.game_number += 1
        self.discard_pile.clear()
        for player in self.players:
            player.hand.clear()
            self.refill_hand(player)

