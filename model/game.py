# -------------------------------------
# game.py
# -------------------------------------

import os
import sys
import uuid

from pydispatch import dispatcher
from twisted.logger import Logger

import ai.protocols.aiprotocol as aiprotocol
from common.constants import Symbol, Status, Errors
from common.ipc import GameStatus, CopyGameStatus
from model.board import Board
from model.events import Events


class Game(object):
    """
    Attributes:
        playerOne
            The human player.
        playerTwo:
            The AI player.
        listeners:
            The game events listeners.
    """

    log = Logger()

    def __init__(self, playerOne=None, playerTwo=None):
        """Inits an instance of the Game class.

        PlayerOne is always the human side of the game.

        Args:
            playerOne (Optional[model.player.Player]):
                The human player (default is None).
            playerTwo (Optional[model.player.Player]):
                The AI player (default is None).

        """

        self.playerOne = playerOne
        self.playerTwo = playerTwo
        self.listeners = list()

        self.aiPlayer = self.playerOne if self.playerOne.isAi \
            else self.playerTwo

        self._board = Board()
        self._uuid = None
        self._moves = list()
        self.status = Status.InProgress
        self.nextPlayer = self.playerOne

        dispatcher.connect(self._onAiMoveResponse, signal=Events.aiResponse)

    @staticmethod
    def create(playerOne, playerTwo):
        """Creates an instance of the Game class.

        Sets the UUID of the new game.

        Args:
            playerOne (model.player.Player)
            playerTwo (model.player.Player)

        Returns:
            An instance of the Game class where the attribute _uuid
            was assigned a value to.

        """
        if playerOne is None:
            raise ValueError('playerOne')

        if playerTwo is None:
            raise ValueError('playerTwo')

        p = Game(playerOne, playerTwo)
        p.uuid = uuid.uuid4()
        return p

    def start(self):
        self.log.info('Starting the game {0}'.format(self.uuid))

        # prepares to launch the AI script
        aiScriptPath = os.getcwd() + "/../ai/aiprocess.py"
        self.log.debug('AI script path is {0!s}'.format(aiScriptPath))

        kwargs = dict()
        aiprotocol.makePipe(bytes(self.uuid),
                            self.aiPlayer.symbol,
                            self.aiPlayer.depth,
                            sys.executable, aiScriptPath,
                            **kwargs)

    def stop(self):
        pass

    def close(self):
        pass

    @property
    def boardData(self):
        return self._board.data

    @property
    def uuid(self):
        """Gets the UUID of the game."""
        return self._uuid

    @uuid.setter
    def uuid(self, uuid):
        """Sets the UUID for this game."""
        if uuid is None:
            raise ValueError("The game's uuid cannot be None or empty.")

        self._uuid = uuid

    def makeMove(self, row, col, symbol):
        """Handles the player's turn.

        Places a piece/symbol on the board at a given position.

        Args:
            row (int):
                The row.
            col (int):
                The column.
            symbol (int):
                The symbol.

        Returns:
            The updated status of the game (common.ipc.GameStatus).

        Raises:
            IndexError.

        """
        self.log.debug('Invoke makeMove with %d, %d, %d' % (row, col, symbol))

        if (row < 0) or (row >= Board.SIZE):
            raise IndexError('Wrong value for the row index: %d' % (row))

        if (col < 0) or (col >= Board.SIZE):
            raise IndexError('Wrong value for the column index: %d' % (col))

        gameStatus = GameStatus(data=self.boardData,
                                turn=self.nextPlayer.symbol,
                                status=self.status,
                                error=Errors.NoError)

        #
        if self.isGameOver():
            self.log.info('The game was over !')
            return gameStatus

        #
        if symbol != self.nextPlayer.symbol:
            self.log.warn("It is not the {0:d} turn's".format(symbol))
            gameStatus.error = Errors.WrongTurn
            return gameStatus

        #
        if self.isLegalMove(row, col):
            self.log.debug('Place the symbol {0:d} at ({1:d}, {2:d})'.
                           format(symbol, row, col))

            self._board.set(row, col, symbol)
            self._moves.append((row, col, symbol))

            self.status = self._computeGameStatus(row, col)
            if self.isGameOver():
                self.log.info('The game is over : {0:d}'.format(self.status))
                dispatcher.send(signal=Events.quit, uuid=self.uuid)
            else:
                self._updateNextSymbol()
                self.log.debug('Game.makeMove - next symbol is {0:d}'.
                               format(self.nextPlayer.symbol))

                gameStatus.turn = self.nextPlayer.symbol

                #
                if self.nextPlayer.symbol == self.aiPlayer.symbol:
                    self._aiMove(row, col)
        else:
            self.log.error('Illegal move')
            gameStatus.error = Errors.IlegalMove

        gameStatus.data = self.boardData
        gameStatus.status = self.status

        return gameStatus

    def isLegalMove(self, row, col):
        """Checks if a piece can be placed on the board at a given position.

        Args:
            row (int): The row.
            col (int): The column.

        Returns:
            bool: True if the piece can be placed on the board,
                    False otherwise.

        """
        self.log.debug('Invoke isLegalMove with (%d, %d)' % (row, col))

        symbol = self._board.get(row, col)
        self.log.debug('symbol = {0!s}'.format(symbol))

        return (not self.isGameOver()) and (symbol == Symbol.Empty)

    def isGameOver(self):
        """Checks whether the game is over.

        Returns:
            bool: True if the game is over, False otherwise.

        """
        self.log.debug('invoking isGameOver: status is {status:d}',
                       status=self.status)
        return (self.status != Status.InProgress)

    def _aiMove(self, row, col):
        """Signals that AI player is to make the next move.

        Args
            row (int):
                The last row coordinate of the human move.
            col (int):
                The last column coordinate of the human move.

        """
        dispatcher.send(signal=Events.aiMove, uuid=self.uuid,
                        row=row, col=col)

    def _onAiMoveResponse(self, uuid, row, col):
        """Handles the Events.AiResponse signal."""

        self.log.debug('_onAiMoveResponse: {uuid}, {row}, {col}',
                       uuid=uuid, row=row, col=col)

        self.log.debug('_onAiMoveResponse: self.uuid = {uuid}',
                       uuid=self.uuid)

        if str(uuid) != str(self.uuid):
            # it's not for this game: ignore the signal
            return

        self.log.debug('AI process responded with: row {row} and col {col}',
                       row=row, col=col)

        #
        gameStatus = None
        if (row == -1) or (col == -1):
            self.log.debug('_onAiMoveResponse: no moves available')
            gameStatus = CopyGameStatus(GameStatus(status=Status.Tie))
        else:
            gameStatus = CopyGameStatus(self.makeMove(row,
                                                      col,
                                                      self.aiPlayer.symbol))

        # try to notify the client that the AI's turn has completed
        if self.listeners:
            for cbk in self.listeners:
                self.log.debug('calling onAiMoved on the remote object')

                d = cbk.callRemote('onAiMoved',
                                   row=row, col=col,
                                   results=gameStatus)

                d.addCallback(lambda _:
                              self.log.debug('remote_onAiMoved succeeded'))

                d.addErrback(lambda reason:
                             self.log.error('remote_onAiMoved failed: {reason}',
                                            reason=reason))

    def _count(self, symbol, row, col, dirI, dirJ):
        """Counts the occurrences of a symbol along a given direction.

        While inside the bounds of the board go in forward and backward
        directions of the direction vector and increment the counter
        while still on the 'side' symbol.

        Args:
            symbol (int): The symbol.
            row (int): The row where the piece/symbol was placed on.
            col (int): The column where the piece/symbol was placed on.
            dirI (int): The row component of the direction vector.
            dirJ (int): The column component of the direction vector.

        Returns:
            int: The number of occurrences of the given symbol.

        """
        count = 0
        i = row
        j = col

        # forward direction
        while (i > -1) and (i < Board.SIZE) and \
                (j > -1) and (j < Board.SIZE) and \
                (self._board.get(i, j) == symbol):
            count += 1
            i += dirI
            j += dirJ

        # backward direction
        i = row - dirI
        j = col - dirJ

        while (i > -1) and (i < Board.SIZE) and \
                (j > -1) and (j < Board.SIZE) and \
                (self._board.get(i, j) == symbol):
            count += 1
            i -= dirI
            j -= dirJ

        self.log.debug('_count: count = {0:d}'.format(count))

        return count

    def _computeGameStatus(self, row, col):
        """Checks if we have a winner or it's a tie.

        Args:
            row (int): The row.
            col (int): The column.

        Returns:
            The status of the game: Status.Tie, Status.X_Won or Status.O_Won.

        """
        self.log.debug('_computeGameStatus: (%d, %d)' % (row, col))

        if self._moves.count == (Board.SIZE ** 2):
            return Status.Tie

        symbol = self._board.get(row, col)

        self.log.debug('_computeGameStatus: symbol is %d' % (symbol))

        if (self._count(symbol, row, col, 1, 0) == Board.SIZE):
            return self._winner(symbol)

        if (self._count(symbol, row, col, 0, 1) == Board.SIZE):
            return self._winner(symbol)

        if (self._count(symbol, row, col, 1, -1) == Board.SIZE):
            return self._winner(symbol)

        if (self._count(symbol, row, col, 1, 1) == Board.SIZE):
            return self._winner(symbol)

        return Status.InProgress

    def _winner(self, symbol):
        """
        """
        return Status.X_Won if symbol == Symbol.X else Status.O_Won

    def _updateNextSymbol(self):
        """Gets the player which can place a piece on the board.

        Args:

        Returns:
            Symbol: the player which makes the next move.

        """
        self.nextPlayer = self.playerOne if self.nextPlayer == self.playerTwo \
            else self.playerTwo
