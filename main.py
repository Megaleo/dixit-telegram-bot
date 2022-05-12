from telegram import User, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (Updater, CommandHandler, InlineQueryHandler,
                          MessageHandler, Filters, CallbackQueryHandler,
                          ChosenInlineResultHandler)
from telegram.error import Unauthorized, InvalidToken
import logging
import sys
from game import DixitGame
from utils import *
from draw import save_results_pic
from random import shuffle, choice

'''
TODO

NICE-TO-HAVE'S -----------------------------------------------------------------

[/] Improve the way results are shown; one of the fun parts of dixit is
    discussing whose answer each person has chosen
    [X] Present results as an image
    [ ] Improve image (how?)

[ ] Allow player to join game in the middle of a match

[ ] Send reminders to late players, skip their turn if need be

[ ] Initial data storage for game analysis

[ ] Let the master manually input the max number of rounds/point

[ ] Use improved card images

[ ] Make clue-writing system more self-evident
    [X] Improve reminder when the storyteller forgets to write a clue
    [ ] Let the storyteller send clue after choosing card? (I tend to be against it)
    [ ] Present instructions when the user writes a "?" inline?

ACESSORIES ---------------------------------------------------------------------

[ ] Confirm that the player's chosen cards were available for choosing, at every
    stage?

[ ] Have the bot reply to the relevant message, instead of sending simple
    messages, when appropriate

[ ] In case a user was already in a game, make it clear whether it's this in
    this same game or in another.

[ ] Debugging
    [/] Create unit tests
        [ ] Automate dummy testing
    [ ] Improve terminal output

[ ] Localization
    [ ] Store display messages in an external file
    [ ] Implement ability to translate to other languages. Test with pt-BR

[ ] Use python 3.10 syntax to improve code

'''

@ensure_game(exists=False)
@ensure_user_inactive
def new_game_callback(update, context):
    '''Runs when /newgame is called. Creates an empty game and adds the master'''
    user = update.message.from_user
    set_game(context)

    get_profile_pic(context.bot, user.id, size=TelegramPhotoSize.SMALL)

    chat = update.effective_chat
    logging.info(f"NEW GAME - name: {chat.title!r}, id: {chat.id}")
    logging.info(f'Master - first_name: {user.first_name}, id: {user.id}')
    print(); logging.info("Stage 0: Lobby!")

    dixit_game = DixitGame(master=user)
    context.chat_data['dixit_game'] = dixit_game
    context.chat_data['results'] = []

    send_message(f"Let's play Dixit!\n"
                 f"The master {dixit_game.master} has created a new game. \n"
                 "Click /join to join and /start to start playing!",
                 update, context,)

    send_message(f'Would you like the game to end based on what?',
                 update, context,
                 reply_markup = InlineKeyboardMarkup.from_column(
                     [InlineKeyboardButton(text,
                         callback_data=f'end settings:{enum}')
                      for enum, text in zip(
                          [c.name for c in dixit_game.end_criteria],
                          ('Until the cards end (official rule)',
                           'Number of points',
                           'Number of rounds',
                           "I don't want it to end!"))])
                     )


@ensure_game(exists=True)
@ensure_user_inactive
@handle_exceptions(TooManyPlayersError, UserAlreadyInGameError)
def join_game_callback(update, context):
    '''Runs when /join is called. Adds the user to the game'''
    set_game(context)
    dixit_game = get_game(context)

    user = update.message.from_user
    get_profile_pic(context.bot, user.id, size=TelegramPhotoSize.SMALL)
    logging.info(f'/join - first_name: {user.first_name}, id: {user.id}')

    dixit_game.add_player(user)
    if dixit_game.stage==0:
        text = f"{user.first_name} was added to the game!"
    else:
        text = f"Welcome {user.first_name}! You may start playing when a new "\
                "round begins"
    send_message(text, update, context)


@ensure_game(exists=True)
@handle_exceptions(HandError, UserIsNotMasterError, GameAlreadyStartedError)
def start_game_callback(update, context):
    '''Runs when /start is called. Does final preparations for the game'''
    dixit_game = get_game(context)
    added_dummies = context.chat_data.get('added_dummies', False)
    user = update.message.from_user
    if len(dixit_game.players) < 3:
        if not added_dummies:
            send_message("There are fewer than 3 players in the game.\n"
                         "How many dummy players do you want to add?",
                         update, context,
                         reply_markup = InlineKeyboardMarkup.from_row(
                             [InlineKeyboardButton(text=str(n),
                                 callback_data=f'dummy settings:{n}')
                              for n in range(5)
                             ])
                        )
            return
        elif len(dixit_game.players) == 2:
            send_message("Playing with two players is not fun... but ok :)",
                         update, context)
        elif len(dixit_game.players) == 1:
            send_message("WARNING: Playing alone won't let you pass the\
                         storyteller's phase. Please get a friend or add a dummy",
                         update, context)

    dixit_game.start_game(user) # can no longer log the chosen cards!
    send_message(f"The game has begun!", update, context)
    storytellers_turn(update, context)


def storytellers_turn(update, context):
    '''Instructs the storyteller to choose a clue and a card'''
    dixit_game = get_game(context)
    print(); logging.info("Stage 1: Storyteller's turn!")
    send_message(f'{dixit_game.storyteller} is the storyteller!\n'
                 'Please write a clue and click on a card.', update, context,
                 button='Click to see your cards!')
    if dixit_game.storyteller.id < 0: # If it's a dummy
        card_id = random_card_from_hand(dixit_game.storyteller)
        simulate_inline(dixit_game.storyteller.user, card_id, 'Beep Boop',
                        update, context)


def query_callback(update, context):
    dixit_game = get_game(context)
    query = update.callback_query

    if update.callback_query.from_user.id != dixit_game.master.id:
        return

    logging.info(f'Query - {query.data!r}')

    setting, value = query.data.split(':')
    if setting == 'play again':
        if value == 'True':
            query.edit_message_text(text='A new game of Dixit begins!')
            dixit_game.restart_game()
            storytellers_turn(update, context)
        else:
            context.chat_data.pop('dixit_game') # frees game data
            del dixit_game
            query.edit_message_text(text='The game has ended.')
        return # return early to avoid the last lines of query_callback

    markup = None
    if setting == 'end settings':
        if value == 'LAST_CARD':
            text = 'Playing by the book, commendable!'
        elif value == 'POINTS':
            text = "Would you like to end the game whenever someone first "\
                   "reaches how many points?"
            markup = InlineKeyboardMarkup.from_row(
                     [InlineKeyboardButton(n, callback_data=f'end value:{n}')
                     for n in (3, 10, 25, 50, 100)]
                     )
        elif value == 'ROUNDS':
            text = "How many rounds would you like the game to last?"
            markup = InlineKeyboardMarkup.from_row(
                     [InlineKeyboardButton(n, callback_data=f'end value:{n}')
                     for n in (1, 3, 5, 10, 25)]
                     )
        elif value == 'ENDLESS':
            text = 'And endless game, nice!'

        else:
            raise ValueError(f'Invalid query!\n{query}')

        if value in [c.name for c in dixit_game.end_criteria]:
            dixit_game.end_criterion = dixit_game.end_criteria[value]

    if setting == 'end value':
        # if the user is sending us endgame values
        number = int(value)
        dixit_game.end_criterion_number = number
        text = f'Alright! The game will last until the number of '\
               f'{dixit_game.end_criterion.name.lower()} is {number}!'

    if setting == 'dummy settings':
        dummies_n = int(value)
        for n in range(1, dummies_n+1):
            dummy_user = User(id=f'{-n}', # Negative id
                               is_bot='False', # Hehe
                               first_name=f'Dummy {n}',
                               )
            dixit_game.add_player(dummy_user)
        context.chat_data['added_dummies'] = True
        text=f'{dummies_n} dummies added to the game!\n'\
              'Please click on /start again'

    query.answer(text='Settings saved!')
    query.edit_message_text(text=text, reply_markup=markup)


def inline_callback(update, context):
    '''Decides what cards to show when a player makes an inline query'''
    user = update.inline_query.from_user
    dixit_game = get_game(context)

    [player] = [p for p in dixit_game.players if p.user == user]
    storyteller = dixit_game.storyteller
    table = dixit_game.table
    stage = dixit_game.stage

    text = '🎴'
    clue = None
    if stage == 1 and player == storyteller:
        cards = player.hand
        clue = update.inline_query.query
    elif stage == 2 and player != storyteller:
        cards = player.hand
    elif stage == 3 and player != storyteller:
        cards = table.values()
        text = '🗳'
    else:
        cards = table.values() if stage==3 else player.hand
        text = f'{player} is impatient...'

    results = [menu_card(card, player, text, clue) for card in cards]
    update.inline_query.answer(results, cache_time=0)


@handle_exceptions(UserNotPlayingError, CardDoesntExistError, ClueNotGivenError,
                   PlayerNotStorytellerError, CardHasNoSenderError, VotingError)
def inline_choices(update, context):
    '''Processes the cards users choose on inline queries'''
    result = update['chosen_inline_result']
    user = result.from_user
    dixit_game = get_game(context)

    card_id = int(result.result_id)
    user_id = user['id']

    card = dixit_game.get_card_by_id(card_id)
    player = dixit_game.get_player_by_id(user_id)
    clue = result.query

    logging.info(f'Inline - {user["first_name"]}, card_id: {card_id}'
                 + f', query: {clue}'*bool(clue))

    if dixit_game.stage == 1:
        dixit_game.storyteller_turn(player=player, card=card, clue=clue)

        print(); logging.info("Stage 2: Others' turn!")

        send_message(f"Now, let the others send their cards!\n"
                     f"{player.name(possessive=True)} clue: *{dixit_game.clue}*",
                     update, context, button='Click to see your cards!',
                     parse_mode='Markdown')

        # The dummies among the other players choose random cards from hand
        other_dummy_players = (player for player in dixit_game.players
                                if player.id < 0 and
                                player != dixit_game.storyteller)
        for dummy in other_dummy_players:
            card_id = random_card_from_hand(dummy)
            simulate_inline(dummy.user, card_id, '', update, context)

    elif dixit_game.stage == 2:
        dixit_game.player_turns(player=player, card=card)

        logging.info(f"Table - ({len(dixit_game.table)}/"
                     f"{len(dixit_game.players)}) cards")
        if dixit_game.stage == 3:
            print(); logging.info("Stage 3: Vote!")
            send_message(f"Hear ye, hear ye! Time to vote!\n"
                         f"{dixit_game.storyteller.name(possessive=True)}"
                         f" clue: *{dixit_game.clue}*",
                         update, context, button='Click to see the table!',
                         parse_mode='Markdown')

            # The dummies among the other players choose random cards from table
            other_dummy_players = (player for player in dixit_game.players
                                    if player.id < 0 and
                                    player != dixit_game.storyteller)
            for dummy in other_dummy_players:
                others_cards = [card for player, card in dixit_game.table.items()
                                if player != dummy]
                card_id = random_card_id(dummy, others_cards)
                simulate_inline(dummy.user, card_id, '', update, context)

    elif dixit_game.stage == 3:
        dixit_game.voting_turns(player=player, card=card)

        logging.info(f"Table - ({len(dixit_game.votes)}/"
                     f"{len(dixit_game.players) - 1}) votes")
        if dixit_game.stage == 0:
            end_of_round(update, context)


def simulate_inline(user, result_id, query, update, context):
    '''Simulates the choice of an inline option by calling inline_choices'''
    fake_result = type('Result', (object,), {'from_user': user,
                       'result_id': result_id, 'query': query})
    update.chosen_inline_result = fake_result
    inline_choices(update, context)


def show_results_text(results, update, context):
    '''Sends the image of the correct answer and send a message with
    who voted for whom.'''
    storyteller_card = results.table[results.storyteller]
    score = results.score
    delta_score = results.delta_score

    send_message(f'The correct answer was...', update, context)
    send_photo(storyteller_card.url, update, context)

    results_text = '\n'.join([f'{player}:  {total_pts} '
                              + f'(+{delta_pts})'if delta_pts else ''
                              for (player, total_pts), delta_pts
                              in zip(score.items(), delta_score.values())])
    vote_list = []
    grouped_votes = {}
    for voter, voted in results.votes.items():
        grouped_votes.setdefault(voted, []).append(voter)
    for voted, voters in grouped_votes.items():
       vote_list.append(f'{voters[0]} \u27f6 {voted}') # bash can't handle char
       for voter in voters[1:]:
           vote_list.append(str(voter))
       vote_list.append('')
    votes_text = '\n'.join(vote_list)

    send_message(results_text, update, context)
    send_message(votes_text, update, context)


def show_results_pic(results, update, context):
    '''Sends results pic'''
    dixit_game = get_game(context)
    n = f'{dixit_game.game_number}.{dixit_game.round_number}'
    results_fn = save_results_pic(results, n=n)
    results_file = open(results_fn, 'rb')
    send_photo(results_file, update, context)


def end_of_round(update, context):
    '''Counts points, resets the appropriate variables for the next round'''
    print(); logging.info('Stage 0: Lobby!')

    dixit_game = get_game(context)
    results = dixit_game.get_results()
    log = 'Results -\n'
    for player in results.players:
        score = results.score[player]
        delta = results.delta_score[player]
        is_st = player==results.storyteller
        vote = results.votes[player] if not is_st else None
        log += f'\t{player.name():<20} - {score} (+{delta}), ' \
              + (f'(voted for {vote})' if not is_st else 'was the Storyteller')\
              + '\n'
    logging.info(log.strip())

    show_results_pic(results, update, context)
    logging.info('Results - Sent image')

    if dixit_game.has_ended():
        end_game(results, update, context)

    else:
        dixit_game.new_round()
        storytellers_turn(update, context)


def end_game(results, update, context):
    max_score = max(results.score.values())
    winners = [p.name() for p in results.score if results.score[p]==max_score]
    if len(winners) == 1:
        text = f'{winners[0]} has won the game! 🎉'
    else:
        text = ', '.join(winners[:-1]) + ' and ' + winners[-1]\
               + ' have won the game! 🎉'
    send_message(text, update, context)
    send_message('Shall we play another match?', update, context,
                 reply_markup = InlineKeyboardMarkup.from_column(
                     [InlineKeyboardButton(
                         text,
                         callback_data=f'play again:{text=="Yes"}')
                      for text in ('Yes', 'No')])
                )


def run_bot(token):
    '''Tells the bot to use the functions we've defined, starts the main loop'''
    updater = Updater(token, use_context=True)
    dispatcher = updater.dispatcher

    # Add commands handlers
    command_callbacks = {'newgame': new_game_callback,
                         'join': join_game_callback,
                         'start': start_game_callback}
    for name, callback in command_callbacks.items():
        dispatcher.add_handler(CommandHandler(name, callback))

    # Add inline handler
    inline_handler = InlineQueryHandler(inline_callback)
    dispatcher.add_handler(inline_handler)

    # Add CallbackQueryHandler for the mid-chat buttons
    dispatcher.add_handler(CallbackQueryHandler(query_callback))

    # Add ChosenInlineResultHandler, to get the user choices made inline
    dispatcher.add_handler(ChosenInlineResultHandler(inline_choices))

    # Start the bot
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    # logging_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging_format = '%(asctime)s - %(levelname)s - %(message)s'
    logging.basicConfig(format=logging_format, level=logging.INFO)
    tokenpath = 'token.txt'
    with open(tokenpath, 'r') as token_file:
        try:
            n = int(sys.argv[1]) # Token number in token.txt
        except (ValueError, IndexError):
            n = 0 # Default to first token

        try:
            token = token_file.readlines()[n].strip() # Remove \n at the end
            run_bot(token)
        except IndexError as e:
            logging.error(f'No token number {n} in {tokenpath}')
            sys.exit(2)
        except (InvalidToken, Unauthorized) as e:
            logging.error(f'Broken token {token}:')
            logging.error(e)
            sys.exit(2)
