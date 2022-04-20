import pytest
import game
from exceptions import *

class User:
    '''class to emulate a telegram user object'''
    def __init__(self, id_, first_name, last_name=''):
        self.first_name = first_name
        self.last_name = last_name
        self.id = id_
    def __eq__(self, other):
        if 'id' not in dir(other):
            return False
        return self.id == other.id


class TestDixitGame:
    @pytest.fixture
    def dixit(self):
        N = 3
        players = [game.Player(User(id_, chr(ord('A') + id_), 'da Silva'))
                   for id_ in range(N)]
        dixit_game = game.DixitGame(master = game.Player(User(-1, 'Master')),
                                    players = players)
        return dixit_game

    def start_game(self, dixit):
        dixit.start_game(dixit.master.user)

    def storyteller_turn(self, dixit):
        st_card = dixit.storyteller.hand[0]
        dixit.storyteller_turn(dixit.storyteller, st_card, 'the clue')

    def player_turns(self, dixit):
        for player in [p for p in dixit.players if p!=dixit.storyteller]:
            card = player.hand[0]
            dixit.player_turns(player, card)

    def voting_turns(self, dixit):
        players = [p for p in dixit.players if p != dixit.storyteller]
        print(dixit.table)
        for player, vote in zip(players, players[1:] + [players[0]]):
            dixit.voting_turns(player, dixit.table[vote])


    def test_init(self, dixit):
        assert dixit.stage == game.Stage.LOBBY
        assert isinstance(dixit.master, game.Player)
        assert dixit.master in dixit.players
        assert len(dixit.cards) == 100
        assert [c.image_id for c in dixit.cards] != list(range(101))
        assert [c.id for c in dixit.cards] != list(range(101))
        assert dixit.draw_pile == dixit.cards
        assert dixit.draw_pile is not dixit.cards
        assert not dixit.has_ended()

    def test_add_player(self, dixit):
        player = game.Player(User(-3, 'New Player', 'da Silva'))
        dixit.add_player(player)
        assert player in dixit.players
        assert player not in dixit.lobby
        other_player = game.Player(User(-4, 'Another New Player', 'da Silva'))
        dixit.stage = game.Stage.VOTE
        assert dixit.stage == game.Stage.VOTE
        dixit.add_player(other_player)
        assert other_player not in dixit.players
        assert other_player in dixit.lobby

    def test_refill_hand(self, dixit):
        player = game.Player(User(-3, 'New Player', 'da Silva'))
        dixit.add_player(player)
        assert player.hand == []
        dixit.refill_hand(player)
        assert len(player.hand) == dixit.cards_per_player

    def test_start_game(self, dixit):
        dixit.start_game(dixit.master.user)
        assert all(len(p.hand)==dixit.cards_per_player for p in dixit.players)
        assert dixit.storyteller in dixit.players
        assert dixit.stage == game.Stage.STORYTELLER

    def test_storyteller_turn(self, dixit):
        # context
        self.start_game(dixit)

        assert dixit.stage == game.Stage.STORYTELLER
        card = dixit.storyteller.hand[0]
        with pytest.raises(ClueNotGivenError):
            dixit.storyteller_turn(dixit.storyteller, card, None)

        self.storyteller_turn(dixit)
        assert dixit.clue == 'the clue'
        assert list(dixit.table.items()) == [(dixit.storyteller, card)]
        assert dixit.stage == game.Stage.PLAYERS

    def test_player_turns(self, dixit):
        # context
        self.start_game(dixit)
        self.storyteller_turn(dixit)

        assert dixit.stage == game.Stage.PLAYERS

        self.player_turns(dixit)
        assert dixit.stage == game.Stage.VOTE
        assert len(dixit.table) == len(dixit.players)
        for player, card in dixit.table.items():
            assert card not in player.hand

    def test_voting_turns(self, dixit):
        # context
        self.start_game(dixit)
        self.storyteller_turn(dixit)
        self.player_turns(dixit)

        assert dixit.stage == game.Stage.VOTE
        with pytest.raises(CardHasNoSenderError):
            dixit.voting_turns(dixit.master, game.Card(-1, -1))
        with pytest.raises(VotingError):
            dixit.voting_turns(dixit.master, dixit.table[dixit.master])

        self.voting_turns(dixit)
        assert dixit.stage == game.Stage.LOBBY
        assert len(dixit.votes) == len(dixit.players) - 1

    def test_point_counter(self, dixit):
        ...

    def test_count_points(self, dixit):
        ...

    def test_new_round(self, dixit):
        '''improve me!'''
        # context
        self.start_game(dixit)
        self.storyteller_turn(dixit)
        self.player_turns(dixit)
        self.voting_turns(dixit)

        old_round_number = dixit.round_number
        dixit.new_round()
        assert dixit.clue == None
        assert dixit.table == {}
        assert dixit.votes == {}
        assert dixit.stage == game.Stage.STORYTELLER
        assert dixit.round_number == old_round_number + 1
        assert all(len(p.hand) == dixit.cards_per_player
                   for p in dixit.players)

    def test_restart_game(self, dixit):
        '''improve me!'''
        # context
        self.start_game(dixit)
        self.storyteller_turn(dixit)
        self.player_turns(dixit)
        self.voting_turns(dixit)

        dixit.restart_game()
        assert dixit.clue == None
        assert dixit.table == {}
        assert dixit.votes == {}
        assert dixit.stage == game.Stage.STORYTELLER
        assert dixit.round_number == 1
        assert all(len(p.hand) == dixit.cards_per_player
                   for p in dixit.players)
