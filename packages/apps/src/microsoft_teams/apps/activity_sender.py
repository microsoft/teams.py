"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from logging import Logger
from typing import Optional

from microsoft_teams.api import (
    ActivityParams,
    ApiClient,
    ConversationReference,
    SentActivity,
)
from microsoft_teams.common import Client, ConsoleLogger

from .http_stream import HttpStream
from .plugins.streamer import StreamerProtocol


class ActivitySender:
    """
    Handles sending activities to the Bot Framework.
    Separate from transport concerns (HTTP, WebSocket, etc.)
    """

    def __init__(self, client: Client, logger: Optional[Logger] = None):
        """
        Initialize ActivitySender.

        Args:
            client: HTTP client with token provider configured
            logger: Optional logger instance for debugging. If not provided, creates a default console logger.
        """
        self._client = client
        self._logger = logger or ConsoleLogger().create_logger("@teams/activity-sender")

    async def send(self, activity: ActivityParams, ref: ConversationReference) -> SentActivity:
        """
        Send an activity to the Bot Framework.

        Args:
            activity: The activity to send
            ref: The conversation reference

        Returns:
            The sent activity with id and other server-populated fields
        """
        # Create API client for this conversation's service URL
        api = ApiClient(service_url=ref.service_url, options=self._client)

        # Merge activity with conversation reference
        activity.from_ = ref.bot
        activity.conversation = ref.conversation

        # Decide create vs update
        if hasattr(activity, "id") and activity.id:
            res = await api.conversations.activities(ref.conversation.id).update(activity.id, activity)
            return SentActivity.merge(activity, res)

        res = await api.conversations.activities(ref.conversation.id).create(activity)
        return SentActivity.merge(activity, res)

    def create_stream(self, ref: ConversationReference) -> StreamerProtocol:
        """
        Create a new activity stream for real-time updates.

        Args:
            ref: The conversation reference

        Returns:
            A new streaming instance
        """
        # Create API client for this conversation's service URL
        api = ApiClient(ref.service_url, self._client)
        return HttpStream(api, ref, self._logger)
