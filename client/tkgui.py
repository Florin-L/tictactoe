"""
    This module implements a GUI client for a tic-tac-toe game.
"""

import os
import sys

# configures the python source path for this module
sys.path.append(os.getcwd() + '\..')

try:
    # for Python2
    import Tkinter as ttk
except ImportError:
    # for Python3
    import tkinter as ttk

import tkMessageBox

from twisted.spread import pb
from twisted.internet import reactor, tksupport
from twisted.logger import Logger
import zope.interface

from pydispatch import dispatcher

from common.constants import Symbol, Status, Errors, PlayerType
from common.ifaces import IGameEventsHandler
from model.game import Board

# events
cmd_newGame = 'cmd_newGame'
cmd_disconnect = 'cmd_disconnect'
cmd_move = 'move'
cmd_resetCell = 'cmd_resetCell'

ev_newGameOk = 'ev_newGameOk'
ev_newGameFailure = 'ev_newGameFailure'

ev_disconnected = 'ev_disconnected'
ev_disconnectedFailed = 'ev_disconnectedFailed'

ev_aiMoved = 'ev_aiMoved'
ev_aiMovedFailure = 'ev_aiMovedFailure'
ev_gameOver = 'ev_gameOver'


class Client(pb.Referenceable):
    """
        This class handles the communication between the client
        and the game which runs on a remote server.
    """

    zope.interface.implements(IGameEventsHandler)
    log = Logger()

    def __init__(self, symbol=Symbol.X):
        self.server = None
        self._symbol = symbol
        self.uuid = None
        self.data = Board
        self.turn = Symbol.X if symbol == Symbol.X else Symbol.O

        self._setupEventHandlers()

    def _connect(self):
        """Connects to the remote server."""
        self.log.debug('Client: _connect')

        cf = pb.PBClientFactory()
        reactor.connectTCP('localhost', 8789, cf)
        d = cf.getRootObject()
        d.addCallbacks(self._server_got, self._err)

    def _disconnect(self):
        """Disconnects from the remote server."""
        d = self.server.callRemote('removeListener',
                                   self.uuid,
                                   self)

        d.addCallback(lambda _: dispatcher.send(signal=ev_disconnected))
        d.addErrback(lambda reason:
                     dispatcher.send(signal=ev_disconnectedFailed,
                                     reason=reason))

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

    def _newGame(self):
        """Initiates the creation of a new game."""
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

    def _onNewGameCreated(self, guid):
        """Called when a new game has been successfully created."""
        self.log.debug('Got uuid {uuid}',
                       uuid=repr(guid))

        self.uuid = guid

        # register for the game events/notifications
        d = self.server.callRemote('addListener',
                                   self.uuid, self)

        d.addCallback(lambda _: dispatcher.send(signal=ev_newGameOk,
                                                guid=guid))
        d.addErrback(lambda failure: dispatcher.send(signal=ev_newGameFailure,
                                                     failure=failure))

    def _onNewGameError(self, failure):
        """Called when the creation of a new game has failed."""
        self.log.error('Failed to create a new game')

    def _makeMove(self, symbol, row, col):
        """Sends a move to the game server."""
        self.log.debug('GUID = {uuid}',
                       uuid=self.uuid)

        d = self.server.callRemote('makeMove',
                                   self.uuid,
                                   symbol,
                                   row, col)

        d.addCallbacks(self._onMakeMove, self._onMakeMoveError)

    def _onMakeMove(self, results):
        """Called when a move has been successfully registered with
        the game server.
        """
        self.log.debug('received: {results}',
                       results=results)

        if results.data is not None:
            self._data = results.data

        if results.error == Errors.IlegalMove:
            self.log.error('Illegal move !')

        self.log.debug('_onMakeMove - status = {status}',
                       status=results.status)

        if results.status != Status.InProgress:
            self.log.info('The game is over (status {status:d})',
                          status=results.status)
            dispatcher.send(signal=ev_gameOver, status=results.status)

    def _onMakeMoveError(self, failure):
        """Called when a 'make move' request has failed."""
        self.log.error('makeMove failed')
        dispatcher.send(signal=ev_aiMovedFailure, failure=failure)

    def remote_onAiMoved(self, row, col, results):
        self.log.debug('remote_onAiMoved - {row}, {col}, {symbol}',
                       row=row, col=col, symbol=results.turn)

        self.log.debug('remote_onAiMoved - status = {status}',
                       status=results.status)

        if results.status != Status.InProgress:
            dispatcher.send(signal=ev_gameOver, status=results.status)

        dispatcher.send(signal=ev_aiMoved,
                        row=row, col=col,
                        symbol=self._getOponent())

    def _getOponent(self):
        return Symbol.X if self._symbol == Symbol.O else Symbol.O

    def _setupEventHandlers(self):
        self.log.debug('Client: _setupEventHandlers')
        dispatcher.connect(self._connect, signal=cmd_newGame)
        dispatcher.connect(self._disconnect, signal=cmd_disconnect)
        dispatcher.connect(self._makeMove, signal=cmd_move)


class Cell(ttk.Label):
    """A cell where a piece will be placed on."""

    def __init__(self, parent, index, symbol):
        """
        Args:
            index (int): The index of the cell.
        """
        ttk.Label.__init__(self, parent,
                           bg='white',
                           fg='black',
                           width=5, height=5)

        self._variable = ttk.StringVar()
        self["textvariable"] = self._variable
        self["justify"] = ttk.CENTER
        self["relief"] = ttk.SUNKEN

        self.index = index
        self.symbol = symbol
        self.bind('<Button-1>', self._onClick)

        dispatcher.connect(self._aiMoved,
                           signal=ev_aiMoved)

        dispatcher.connect(self._resetContent,
                           signal=cmd_resetCell)

    def set(self, value):
        self._variable = value

    def _onClick(self, ev):
        if not App.isConnected:
            tkMessageBox.showerror('Warn',
                                   'Client is not registered with the server !')
            return

        if App.isGameOver:
            tkMessageBox.showinfo('Info',
                                  'The game was over !')
            return

        self._variable.set('X' if self.symbol == Symbol.X else 'O')

        # notify the listeners
        row, col = self.index / 3, self.index % 3
        dispatcher.send(signal=cmd_move, symbol=self.symbol,
                        row=row, col=col)

    def _aiMoved(self, row, col, symbol):
        if (row == -1) or (col == -1):
            return

        if self.index == (row * 3 + col):
            s = 'X' if symbol == Symbol.X else 'O'
            self._variable.set(s)

    def _resetContent(self):
        self._variable.set('')


class App(ttk.Tk):
    """The client application."""

    log = Logger()
    isConnected = False
    isGameOver = False

    def __init__(self, parent, symbol=Symbol.X):
        ttk.Tk.__init__(self, parent)
        self.parent = parent
        self.title = 'GUI client'
        self.symbol = symbol
        #
        self._initialize()
        self._setupEventHandlers()
        #
        self.c = Client(symbol)

    def _initialize(self):
        """Initializes the UI."""
        # creates the Grid manager
        self.grid()

        # creates the widgets
        exitBtn = ttk.Button(self, text=u'Exit', command=self._quit)
        exitBtn.grid(row=0, column=0,
                     padx=5, pady=5,
                     sticky='E')

        self.newGameBtn = ttk.Button(self, text=u'New game',
                                     command=self._onNewGame)
        self.newGameBtn.grid(row=0, column=1,
                             padx=5, pady=5,
                             sticky='W')

        for i in xrange(3):
            for j in xrange(3):
                cell = Cell(self, i * 3 + j, self.symbol)
                cell.grid(row=i + 1, column=j, sticky='WENS')

        #
        for i in xrange(3):
            self.grid_columnconfigure(i, weight=1)
            self.grid_rowconfigure(i + 1, weight=1)

    def _quit(self):
        """Sends the disconnecting signal to the listeners and then exits."""
        dispatcher.send(signal='cmd_disconnect')

        if not App.isConnected:
            reactor.stop()

    def _onNewGame(self):
        self.log.debug('_onNewGame')
        # dispatcher.send(signal=cmd_newGame)
        self.c._connect()

    def _setupEventHandlers(self):
        """Sets up the signal handlers."""
        dispatcher.connect(self._connected,
                           signal=ev_newGameOk)
        dispatcher.connect(self._connected_failed,
                           signal=ev_newGameFailure)
        dispatcher.connect(self._aiMoved,
                           signal=ev_aiMoved)
        dispatcher.connect(self._disconnected,
                           signal=ev_disconnected)
        dispatcher.connect(self._disconnected_failed,
                           signal=ev_disconnectedFailed)
        dispatcher.connect(self._on_gameover,
                           signal=ev_gameOver)

    def _connected(self, guid):
        """Handles the signal 'ev_newGameOk'."""
        App.isConnected = True
        self.log.info('App - connected to game {guid}', guid=guid)

        self.newGameBtn.config(state='disabled')
        self._resetBoard()
        App.isGameOver = False

        tkMessageBox.showinfo('Info', 'A new game has been created.')

    def _connected_failed(self, failure):
        """Handles the signal 'ev_newGameFailure'."""
        App.isConnected = False
        self.log.error('App - failed initiate a game (reason: {reason})',
                       reason=failure)

    def _aiMoved(self, row, col):
        """Handles the signal 'ev_aiMoved'."""
        self.log.debug('_aiMoved - row {row}, col {col}', row=row, col=col)

    def _disconnected(self):
        """Handles the signal 'ev_disconnected'."""
        self.log.info('The client has been disconnected from the game server.')
        reactor.stop()

    def _disconnected_failed(self, reason):
        """Handles the signal 'ev_disconnectedFailed'."""
        self.log.error(
                'The client failed to be disconnected from the game server.')
        reactor.stop()

    def _resetBoard(self):
        dispatcher.send(signal=cmd_resetCell)

    def _on_gameover(self, status):
        """Handles the signal 'ev_gameOver."""
        self.log.info('The game is over: status = {status}',
                      status=status)

        App.isGameOver = True
        self.newGameBtn.config(state='normal')

        s = None
        if status == Status.Tie:
            s = 'Tie'
        elif status == Status.X_Won:
            s = 'X won !'
        elif status == Status.O_Won:
            s = 'O won !'
        else:
            s = 'WTF ???'

        tkMessageBox.showinfo('Info',
                              'The game is over: {result}'.format(result=s))


def main():
    from twisted.python import log
    log.startLogging(sys.stdout)

    symbol = Symbol.X
    if len(sys.argv) > 1:
        arg = sys.argv[1].strip().lower()
        symbol = Symbol.X if arg == 'x' else Symbol.O

    log.msg('The symbol for the human player is ', symbol)

    app = App(None, symbol)
    app.eval('tk::PlaceWindow %s center' % app.winfo_pathname(app.winfo_id()))

    tksupport.install(app)
    reactor.run()


if __name__ == '__main__':
    main()
