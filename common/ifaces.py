#
# ifaces.py
#
# Declares the class interfaces.
#

import zope.interface


class IGameEventsHandler(zope.interface.Interface):
    """Declares the handlers for the game events/notifications.
    """

    def remote_onAiMoved(self, row, col, results):
        """Handles the AI player's move."""
