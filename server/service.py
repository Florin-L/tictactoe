import sys
from twisted.spread import pb
from twisted.internet import reactor
from twisted.python import log
from game_server import GameServer


if __name__ == '__main__':
    log.startLogging(sys.stdout)

    log.msg('Initializing the server factory')
    server_factory = pb.PBServerFactory(GameServer())
    reactor.listenTCP(8789, server_factory)

    log.msg('The game service is listening for requests')
    reactor.run()
