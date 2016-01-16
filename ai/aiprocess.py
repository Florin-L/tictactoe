import os
from random import seed, randint

from twisted.internet import reactor
from twisted.internet import stdio
from twisted.logger import Logger
from twisted.protocols import basic
from twisted.python import log
from twisted.python.logfile import DailyLogFile


class AiPlayerProtocol(basic.LineReceiver):
    """
    The AI process Standard IO protocol.
    """

    delimiter = '\n'
    log = Logger()

    def __init__(self):
        self.uuid = None
        self.symbol = None
        self.depth = None
        self._moves = list(xrange(9))

    def connectionMade(self):
        self.log.info('AI Process has connected to pipes.')

    def lineReceived(self, line):
        self.log.debug('line: {line:s}', line=line)
        # do not process the blank lines
        if not line:
            return

        # process command
        cmdParts = line.split()
        cmd = cmdParts[0].lower()
        args = cmdParts[1:]

        # dispatch the command to the appropriate method
        try:
            method = getattr(self, '_do_' + cmd)
        except AttributeError, e:
            self.log.failure('No such command {msg!s}', msg=e)
            self.sendLine('Error: no such command (%s)' % (cmd))
        else:
            try:
                method(*args)
            except Exception, e:
                self.log.failure('Exception caught: {e}', e=e)
                self.sendLine('Error: ' + str(e))

    def connectionLost(self, reason):
        self.log.info('Connection lost from {peer:s}',
                      peer=self.transport.getPeer())

    def _do_init(self, gameUuid, symbol, depth):
        self._createLogFile(gameUuid)

        self.log.debug('uuid {uuid}, symbol {symbol}, depth {depth}',
                       uuid=gameUuid, symbol=symbol, depth=depth)

        self.uuid = gameUuid
        self.symbol = int(symbol)
        self.depth = int(depth)

    def _do_move(self, gameUuid, row, col):
        self.log.debug('_do_move: uuid {uuid}, human move ({row}, {col})',
                       uuid=gameUuid, row=row, col=col)

        if len(self._moves) == 0:
            self.log.error('_do_move: no more available moves')
            return

        self.log.debug('_moves before: {moves}', moves=self._moves)

        i, j = int(row), int(col)
        self._moves.remove(i * 3 + j)

        # choose the move randomly
        self.log.debug('len(self._moves) = {l}', l=len(self._moves))

        if len(self._moves) == 0:
            self.log.debug('there is no available solution')
            self.sendLine("MOVE {uuid} {row:d} {col:d}".format(uuid=gameUuid,
                                                               row=-1,
                                                               col=-1))
            return
        else:
            seed()
            n = randint(0, len(self._moves) - 1)
            m = self._moves[n]

        self._moves.remove(m)

        self.log.debug('selected position: {m}', m=m)
        self.log.debug('_moves after: {moves}', moves=self._moves)

        # send back the response
        self.sendLine("MOVE {uuid} {row:d} {col:d}".format(uuid=gameUuid,
                                                           row=m / 3,
                                                           col=m % 3))

    def _do_quit(self, uuid):
        self.log.debug("Quitting the game {uuid}", uuid=uuid)
        self.transport.loseConnection()
        reactor.stop()

    def _createLogFile(self, uuid):
        logDirPath = '{cwd}\\..\\logs\\aiprocesses'.format(cwd=os.getcwd())
        if not os.path.exists(logDirPath):
            os.mkdir(logDirPath)

        logFilePath = '{dir}\\{uuid}.log'.format(dir=logDirPath, uuid=uuid)
        log.startLogging(DailyLogFile.fromFullPath(logFilePath))


def main():
    """The main function.
    """

    stdio.StandardIO(AiPlayerProtocol())
    reactor.run()

    log.msg('Bye !')


if __name__ == '__main__':
    main()
