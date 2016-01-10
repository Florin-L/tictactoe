from __future__ import print_function
import sys
import os
from twisted.spread import pb, jelly
from twisted.internet import reactor
from twisted.logger import Logger
import zope.interface

# configures the python source path for this module
sys.path.append(os.getcwd() + '/..')

from common.constants import Symbol, PlayerType, \
    Status, Errors
from model.game import Board
from common.ifaces import IGameEventsHandler


class ConsoleClient(pb.Referenceable):
    """
    A console client for the TicTacToe game server.
    """

    zope.interface.implements(IGameEventsHandler)

    log = Logger()

    def __init__(self, symbol=Symbol.X):
        self._gameGuid = None
        self._symbol = symbol
        self._data = Board()
        self._turn = Symbol.X if symbol == Symbol.X else Symbol.O

    def connect(self):
        """Connects to the game server.

        Initiates the connection with the game server:
            - connects to the localhost server on a given port
            - tries to acquire the root object
            - registers two callbacks to be called:
                - self._server_got
                    if the acquisition of the root object succeeded
                - self._err
                    if the acquisition of the root object failed

        """
        client_factory = pb.PBClientFactory()
        reactor.connectTCP('localhost', 8789, client_factory)
        d = client_factory.getRootObject()
        d.addCallbacks(self._server_got, self._err)

    def _newGame(self):
        """Initiates the creation of a new game.
        """
        playerOneSymbol = self._symbol if self._symbol == Symbol.X \
            else Symbol.O

        playerOneType = PlayerType.Human if self._symbol == Symbol.X \
            else PlayerType.Ai

        playerTwoSymbol = Symbol.O if playerOneSymbol == Symbol.X \
            else Symbol.X

        playerTwoType = PlayerType.Human if playerOneType == PlayerType.Ai \
            else PlayerType.Ai

        d = self.server.callRemote('createGame',
                                   playerOneSymbol=playerOneSymbol,
                                   playerOneType=playerOneType,
                                   playerTwoSymbol=playerTwoSymbol,
                                   playerTwoType=playerTwoType,
                                   searchDepth=0)

        d.addCallbacks(self._onNewGameCreated, self._onNewGameError)

    def _makeMove(self, symbol, row, col):
        """Sends a move to the game server.
        """
        self.log.debug('GUID = {uuid}',
                       uuid=self._gameGuid)

        d = self.server.callRemote('makeMove',
                                   self._gameGuid,
                                   symbol,
                                   row, col)

        d.addCallbacks(self._onMakeMove, self._onMakeMoveError)

    def _onNewGameCreated(self, guid):
        """Called when a new game has been successfully created.
        """
        self.log.debug('Got uuid {uuid}',
                       uuid=repr(guid))

        self._gameGuid = guid

        # register for the game events/notifications
        d = self._registerClient()

        d.addCallback(lambda _: self._processNextCommand())

        # d.addErrback(lambda reason: self._quit(reason))

    def _onNewGameError(self, failure):
        """Called when the creation of a new game has failed.
        """
        self.log.error('Failed to create a new game')
        self._quit()

    def _onMakeMove(self, results):
        """Called when a move has been successfully registered by
        the game server.
        """
        self.log.debug('received: {results}',
                       results=results)

        if results.data is not None:
            self._data = results.data
            self._drawBoard()

        if results.error == Errors.IlegalMove:
            self.log.error('Illegal move !')

        if results.status != Status.InProgress:
            #
            self.log.info('The game is over (status {status:d})',
                          status=results.status)
            self._quit()
            return

        #
        self._turn = results.turn

        # process the next command
        self._processNextCommand()

    def _onMakeMoveError(self, failure):
        """Called when a 'make move' request has failed.
        """
        self.log.error('makeMove failed')
        print(failure)

        if failure.type == jelly.InsecureJelly:
            self.log.error('makeMove: insecure jelly')

        # process the next command
        self._processNextCommand()

    def _server_got(self, obj):
        """Called when the server root object has been successfully acquired.
        """
        self.log.info('got the server object')
        self.server = obj

        self.log.info('initiating a new game')
        self._newGame()

    def _err(self, reason):
        """Called when the acquiring of the server root object has failed.
        """
        self.log.error('error getting object (reason: {reason!s}',
                       reason=reason)
        self.log.info('shutting down')

        self._quit()

    def _drawBoard(self):
        s = ""
        for i in xrange(0, 3):
            for j in xrange(0, 3):
                symbol = int(self._data[i * 3 + j])
                if symbol == Symbol.Empty:
                    s += ' _ '
                elif symbol == Symbol.X:
                    s += ' X '
                elif symbol == Symbol.O:
                    s += ' O '
                else:
                    raise AssertionError('Invalid value for symbol.')

            s += '\n\n'

        print(s)

    def _processNextCommand(self):
        """Reads from the console and processes the next command.
        """
        print("It is {0:s} turn.".
              format('X' if self._turn == Symbol.X else 'O'))

        if self._turn != self._symbol:
            print('Waiting for the opponent move ...')
            return

        print('Enter the move (symbol row count) or \'q|Q\' to exit: ')
        cmd = sys.stdin.readline().strip().lower()

        if cmd == 'q':
            # exit
            self._quit()
            return

        tokens = cmd.split()
        if len(tokens) == 3:
            s, r, c = tokens

            s = s.lower()
            if s != 'x' and s != 'o':
                # exit
                self._quit()
                return

            row = int(r.strip())
            col = int(c.strip())
            symbol = Symbol.X if s == 'x' or s == 'X' else Symbol.O

            self._makeMove(symbol, row, col)

    def _quit(self, msg=None):
        if msg:
            self.log.debug('_quit: {msg!s}', msg=msg)

        self.log.info('Exiting the application')

        d = self._unregisterClient()

        d.addCallback(lambda _: self._exit())
        d.addErrback(lambda _: self._exit())

    def _exit(self):
        """Stops the reactor and exits the application.
        """
        if reactor.running:
            reactor.stop()

        self.log.info('Bye !')

    def _reverseSymbol(self, symbol):
        return Symbol.O if symbol == Symbol.X else Symbol.X

    #
    def remote_onAiMoved(self, row, col, results):
        """Handles the AI player's move.
        """
        self.log.debug('onAiMoved: row {row}, col {col}'.format(row=row,
                                                                col=col))

        self.log.debug('received: {results}', results=results)

        if results.data is not None:
            self._data = results.data
            self._drawBoard()

        if results.error == Errors.IlegalMove:
            self.log.error('Illegal move !')

        if results.status != Status.InProgress:
            self.log.info('The game is over (status {status:d})',
                          status=results.status)
            self._quit()
            return

        #
        self._turn = results.turn
        #
        self._processNextCommand()

    def _registerClient(self):
        """Registers with the game server for notifications.
        """
        self.log.info('_registerClient')
        d = self.server.callRemote('addListener',
                                   self._gameGuid, self)
        return d

    def _unregisterClient(self,):
        """Unregisters from the game notifications.
        """
        d = self.server.callRemote('removeListener',
                                   self._gameGuid, self)
        return d


if __name__ == '__main__':
    from twisted.python import log
    log.startLogging(sys.stdout)

    log.msg(sys.argv)
    symbol = Symbol.X

    if len(sys.argv) > 1:
        arg = sys.argv[1].strip().upper()
        if arg == 'X':
            symbol = Symbol.X
        elif arg == 'O':
            symbol = Symbol.O
        else:
            raise ValueError('Unknown symbol {0:d}'.format(symbol))

    ConsoleClient(symbol).connect()
    reactor.run()
