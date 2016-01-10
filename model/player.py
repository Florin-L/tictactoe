# -------------------------------------
# player.py
# -------------------------------------

from common.constants import PlayerType, Symbol


class Player(object):
    """

    Encapsulates the player's attributes (type, symbol and the search depth).
    Provides a factory function to create instances of the class Player.

    """

    def __init__(self, type=PlayerType.Human, symbol=Symbol.X, depth=0):
        """Inits an instance of the class Player.

        Args:
            type (Optional[int]): The player type (Human or AI).
            symbol (Optional[int]): The player's symbol (X or O).
            depth (Optional[int]): The search depth for the AI player.
        """
        self._type = type
        self._symbol = symbol

        self.searchDepth = None
        if self._type == PlayerType.Ai:
            self.searchDepth = depth if depth <= 4 else 4

    @property
    def symbol(self):
        """Gets the player's symbol."""
        return self._symbol

    @symbol.setter
    def symbol(self, symbol):
        """Sets the player's symbol."""
        if (symbol == Symbol.X) or (symbol == Symbol.O):
            self._symbol = symbol
        else:
            raise ValueError('Illegal value for symbol: {0:d}'.
                             format(symbol))

    @property
    def type(self):
        """Gets the player's type."""
        return self._type

    @type.setter
    def type(self, type):
        """Sets the player's type."""
        if (type == PlayerType.Human) or (type == PlayerType.Ai):
            self._type = type
        else:
            raise ValueError('Illegal value for the player type: {0:d}'.
                             format(type))

    @property
    def isHuman(self):
        """Returns True if this is an human player, False otherwise."""
        return self.type == PlayerType.Human

    @property
    def isAi(self):
        """Returns True if this is an AI player, False otherwise."""
        return self.type == PlayerType.Ai

    @staticmethod
    def playerBuilder():
        """Creates and returns a player builder."""
        return PlayerBuilder()

    @staticmethod
    def create(type, symbol, **kwargs):
        """Creates an instance of the class Player and set the attributes.

        Args:
            type (int): The player type (Human or AI).
            symbol (int): The player's symbol (X or O).
            **kwargs :

        Returns:
            The instance of the Player class.

        """
        p = Player()
        p.type = type
        p.symbol = symbol

        if kwargs['depth'] is not None:
            depth = int(kwargs['depth'])
            p.depth = depth if depth <= 4 else 4

        return p


class PlayerBuilder(object):
    """A fluid builder for the Player instances."""

    def __init__(self):
        self._player = Player()

    def type(self, type):
        """Sets the player type."""
        self._player.type = type
        return self

    def symbol(self, symbol):
        """Sets the player's symbol."""
        self._player.symbol = symbol
        return self

    def searchDepth(self, depth):
        """Sets the search depth."""
        self._player.depth = depth
        return self

    def build(self):
        """Returns the player."""
        return self._player
