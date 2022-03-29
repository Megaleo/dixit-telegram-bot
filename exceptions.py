class GameException(Exception):
    pass

class UserAlreadyInGameError(GameException):
    pass

class TooManyPlayersError(GameException):
    pass

class UserNotMasterError(GameException):
    pass

class GameAlreadyStartedError(GameException):
    pass

class UserNotPlayingError(GameException):
    pass

class CardDoesntExistError(GameException):
    pass

class PlayerNotStorytellerError(GameException):
    pass

class ClueError(GameException):
    pass

class StageError(GameException):
    pass

class CardHasNoSenderError(GameException):
    pass

