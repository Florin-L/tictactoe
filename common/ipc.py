# -------------------------------------
# ipc.py
# The IPC objects.
# -------------------------------------

from twisted.spread import pb
from common.constants import Errors


class GameStatus:
    """

    Attributes:
        data (list[str]):
        turn (int):
        status (int): The status of the game:
            0 - tie
            1 - X won
            2 - O won
            3 - in progress
        error (int): The error code.

    """

    def __init__(self,
                 data=None, turn=None,
                 status=None, error=Errors.NoError):
        self.data = data
        self.turn = turn
        self.status = status
        self.error = error

    def __str__(self):
        s = ''
        for c in self.data:
            s += c

        return \
            "data:'{data}', turn:{turn}, status:{status}, error:{error}".format(
                data=c, turn=self.turn,
                status=self.status, error=self.error)


class CopyGameStatus(pb.Copyable, pb.RemoteCopy):
    """
    Server to Client only.

    Attributes:
        data (list[str])
        turn (int):
        status (int): The status of the game:
            0 - tie
            1 - X won
            2 - O won
            3 - in progress
        error (int): The error code.

    """

    def __init__(self, game_status):
        self.data = game_status.data
        self.turn = game_status.turn
        self.status = game_status.status
        self.error = game_status.error

pb.setUnjellyableForClass(CopyGameStatus, CopyGameStatus)
