# -------------------------------------
# game_server.py
# -------------------------------------

import sys
import os
import uuid
from twisted.spread import pb
from twisted.logger import Logger

# configures the python source path for this module
sys.path.append(os.getcwd() + '/..')

from model.game import Game
from model.player import Player
from common.ipc import CopyGameStatus


class GameServer(pb.Root):
    """The games server."""

    log = Logger()

    def __init__(self):
        self._games = {}

    def remote_createGame(self, playerOneSymbol, playerOneType,
                          playerTwoSymbol, playerTwoType,
                          searchDepth=0,
                          cbk=None):
        """Creates a new Game object.

        Args:
            playerOneSymbol (int)
            playerOneType (int)
            playerTwoSymbol (int)
            playerTwoType (int)
            searchDepth (Optional[int])

        Returns:
            UUID: The UUID of the newly created game.

        Raises:
            ValueError

        """
        # creates the game
        playerOne = Player.playerBuilder().symbol(playerOneSymbol). \
            type(playerOneType).build()

        playerTwo = Player.playerBuilder().symbol(playerTwoSymbol). \
            type(playerTwoType).build()

        if playerOne.isAi:
            playerOne.depth = searchDepth
        elif playerTwo.isAi:
            playerTwo.depth = searchDepth
        else:
            raise ValueError('No AI player')

        game = Game.create(playerOne, playerTwo)

        # stores the game in our map
        self._games[game.uuid] = game

        # returns the GUID back to the caller
        self.log.info('A new game ({uuid}) was created', uuid=game.uuid)

        # starts the game
        try:
            game.start()
        except Exception, e:
            self.log.failure('Failed to start the game {0}. Reason: {1}'.
                             format(game.uuid, str(e)))

        return bytes(game.uuid)

    def remote_closeGame(self, gameGuid):
        """
        """
        g = self._games[gameGuid]
        if g is None:
            raise Exception('remote_closeGame : \
                no such game with guid: %s' % (repr(gameGuid)))

        # 'closes' the game
        g.close()

        # removes the game instance from our map
        self._games.keys().remove(gameGuid)

    def remote_addListener(self, game_uuid, obj):
        """Adds an events listener for a game instance.
        """
        guid = uuid.UUID('{%s}' % game_uuid)
        self.log.debug('addListener for game {guid!s}', guid=guid)

        game = self._games.get(guid)
        if game:
            self.log.debug('listener for game {guid!s} added', guid=guid)
            game.listeners.append(obj)
        else:
            self.log.error('No game with the uiid={guid!s}', uuid=guid)

    def remote_removeListener(self, game_uuid, obj):
        """Removes an event listeners for a game instance.
        """
        guid = uuid.UUID('{%s}' % game_uuid)
        game = self._games.get(guid)
        if game:
            game.listeners.remove(obj)
            self.log.debug('listener for game {guid!s} removed', guid=guid)
        else:
            self.log.error('No game with the uiid={uuid}', uuid=guid)

    def remote_makeMove(self, gameGuid, player, row, col):
        """Handles a human player move.

        Args:
            gameGuid: The GUID of the game.
            player: The symbol (X or O).
            row: The row.
            col: The column.

        Returns:
            The status of the game board.

        Raises:
            ValueError, LookupError.

        """
        if gameGuid is None:
            raise ValueError('remote_makeMove: gameGuid is None')

        guid = uuid.UUID(gameGuid)

        self.log.info("Invoking remote_makeMove with:\
            %s, %s, %d, %d" % (guid, player, row, col))

        g = self._games[guid]
        if g is None:
            raise LookupError('remote_makeMove: \
                no such game with guid: %s' % (bytes(gameGuid)))

        self.log.debug('remote_makeMove:\
            place a \'%s\' at (%d, %d)' % (player, row, col))

        try:
            gameStatus = g.makeMove(row, col, player)

            self.log.debug('gameStatus: {status!s}',
                           status=gameStatus)

            # convert to the sender game protocol
            copyGameStatus = CopyGameStatus(gameStatus)

            self.log.debug('remote_makeMove returns: {data!s}',
                           data=copyGameStatus.data)

            return copyGameStatus

        except Exception as e:
            self.log.failure('Exception caught: {msg}', msg=e.message)
            raise e

    def remote_isLegalMove(self, gameGuid, player, row, col):
        """
        """
        g = self._games[gameGuid]
        if g is not None:
            return g.isLegalMove(row, col)

        raise LookupError('remote_isLegalMove: \
            no such game with guid: %s' % (bytes(gameGuid)))
