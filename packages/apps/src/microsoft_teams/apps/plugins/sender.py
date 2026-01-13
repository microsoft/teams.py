"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from abc import abstractmethod

from microsoft_teams.api.activities import ActivityParams, SentActivity
from microsoft_teams.api.models import ConversationReference

from .plugin_base import PluginBase
from .streamer import StreamerProtocol


class Sender(PluginBase):
    """A plugin that can send activities"""

    @abstractmethod
    async def send(
        self, activity: ActivityParams, ref: ConversationReference, *, is_targeted: bool = False
    ) -> SentActivity:
        """Called by the App to send an activity"""
        pass

    @abstractmethod
    def create_stream(self, ref: ConversationReference) -> StreamerProtocol:
        """Called by the App to create a new activity stream"""
        pass
