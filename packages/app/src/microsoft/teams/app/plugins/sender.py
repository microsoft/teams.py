"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from abc import abstractmethod

from microsoft.teams.api.clients.conversation import ActivityParams
from microsoft.teams.api.models import ConversationReference, Resource

from .plugin import Plugin
from .streamer import StreamerProtocol


class Sender(Plugin):
    """A plugin that can send activities"""

    @abstractmethod
    async def send(self, activity: ActivityParams, ref: ConversationReference) -> Resource:
        """Called by the App to send an activity"""
        pass

    @abstractmethod
    def create_stream(self, ref: ConversationReference) -> StreamerProtocol:
        """Called by the App to create a new activity stream"""
        pass
