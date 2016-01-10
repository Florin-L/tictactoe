# -------------------------------------
# board.py
# -------------------------------------

from twisted.logger import Logger
from common.constants import Symbol


class Board(object):
    """Keeps the board status.
    """
    SIZE = 3
    log = Logger()

    def __init__(self):
        self.data = ['0'] * (Board.SIZE ** 2)
        self.log.debug('Board: %s' % (repr(self.data)))

    def set(self, row, col, symbol):
        """
        """
        self.data[row * Board.SIZE + col] = str(symbol)

    def get(self, row, col):
        """
        """
        return int(self.data[row * Board.SIZE + col])

    def __str__(self):
        s = ""
        for i in xrange(0, Board.SIZE):
            for j in xrange(0, Board.SIZE):
                if self.get(i, j) == Symbol.Empty:
                    s += ' _ '
                elif self.get(i, j) == Symbol.X:
                    s += ' X '
                elif self.get(i, j) == Symbol.O:
                    s += ' O '
                else:
                    raise AssertionError('Invalid value for symbol.')

            s += '\n\n'

        return s
