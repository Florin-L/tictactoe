
class Status:
    """
    The game status:
        Tie
        Player 'X' won
        Player 'O' won
    """
    Tie = 0
    X_Won = 1
    O_Won = 2
    InProgress = 3


class Symbol:
    """
    The symbol: X or 0.
    """
    Empty = 0
    X = 1
    O = 2


class PlayerType:
    """
    The player type: Human or Ai.
    """
    Human = 0
    Ai = 1


class Errors:
    """
    """
    NoError = 0
    IlegalMove = 1
    WrongTurn = 2
