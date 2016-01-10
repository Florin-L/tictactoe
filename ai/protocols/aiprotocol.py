from twisted.internet import protocol, reactor
from twisted.logger import Logger
from pydispatch import dispatcher
from model.events import Events


class AiProcessProtocol(protocol.ProcessProtocol):
    """

    Attributes:
        symbol (int):
            The symbol (X or O) for the AI player.
        depth (int):
            The search depth.
        uuid  (bytes):
            The UUID of the game.

    """

    log = Logger()

    def __init__(self, uuid, symbol, depth):
        """
        Args:
            uuid:
                The UUID of the game.
            symbol:
                The symbol for the AI player.
            depth:
                The search depth for AI player.

        """

        self.uuid = uuid
        self.symbol = symbol
        self.depth = depth

        self.log.debug('symbol {symbol}, depth {depth}, uuid {uuid}',
                       symbol=self.symbol, depth=self.depth, uuid=self.uuid)

        dispatcher.connect(self._onAiMoveRequest, signal=Events.aiMove)

    def connectionMade(self):
        self.log.debug('Sending INIT command.')
        self._sendInitCmd()

    def outReceived(self, data):
        self.log.debug('AiProtocol.outReceived - received: {data!s}',
                       data=data)

        if 'Error:' in data:
            self.log.error('Error received from AI process: {msg}',
                           msg=data)
            return

        data = data.strip()
        self.log.debug('AI process response: {data}',
                       data=data)
        self._handleResponse(data)

    def errReceived(self, data):
        pass

    def inConnectionLost(self):
        pass

    def outConnectionLost(self):
        pass

    def processExited(self, reason):
        self.log.info('Process exited: status {status:d}',
                      status=reason.value.exitCode)

    def processEnded(self, reason):
        self.log.info('Process ended: status {status:d}',
                      status=reason.value.exitCode)
        self.log.info('Quitting the AI player')

    def _sendInitCmd(self):
        """Sends the 'INIT' command to the AI process."""
        cmd = 'INIT {0:s} {1:d} {2:d}\n'.format(self.uuid,
                                                self.symbol,
                                                self.depth)
        self.transport.write(cmd)

    def _sendMoveCmd(self, row, col):
        """Sends the command 'MOVE' to the AI process."""
        cmd = 'MOVE {uuid:s} {row:d} {col:d}\n'.format(uuid=self.uuid,
                                                       row=row,
                                                       col=col)
        self.transport.write(cmd)

    def _onAiMoveRequest(self, uuid, row, col):
        """Handler for the signal Events.aiMove."""
        if str(self.uuid) != str(uuid):
            return

        self.log.debug('Handle aiMove request for game {uuid}', uuid=uuid)
        self._sendMoveCmd(row, col)

    def _on_move(self, uuid, row, col):
        """Handles the AiMove response."""
        self.log.debug('_on_move: UUID = {uuid}, self.uuid={uuid2}',
                       uuid=uuid, uuid2=self.uuid)

        self.log.debug('_on_move: type(uuid) = {t}, type(self.uuid) = {t2}',
                       t=type(uuid), t2=type(self.uuid))

        if str(self.uuid) != str(uuid):
            return

        i = int(row)
        j = int(col)

        self.log.debug('_on_move: game {uuid} row {row} col {col}',
                       uuid=uuid,
                       row=i,
                       col=j)

        dispatcher.send(Events.aiResponse, uuid=self.uuid, row=i, col=j)

    def _handleResponse(self, res):
        """Handles the AI process responses."""
        if res is None:
            return

        # process the response
        resParts = res.split(" ")
        cmd = resParts[0].lower()
        resArgs = resParts[1:]

        self.log.debug('handleResponse: {cmd}, {args}',
                       cmd=cmd, args=resArgs)

        # dispatch the response to the appropriate method
        name = '_on_' + cmd
        try:
            method = getattr(self, name)
        except AttributeError:
            self.log.error('No such method {method}',
                           method=name)
        else:
            try:
                self.log.debug('{name}, {method}', name=name, method=method)
                method(*resArgs)
            except Exception, e:
                self.log.failure('Exception caught: {e}', e=e)


def makePipe(uuid, symbol, depth, cmd, *args, **kwargs):
    #
    pipe = AiProcessProtocol(uuid, symbol, depth)
    #
    args = [cmd] + list(args)
    reactor.spawnProcess(pipe, cmd, args)
