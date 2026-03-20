"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import logging
from typing import cast

from microsoft_teams.api import (
    ActivityParams,
    ApiClient,
    ConversationReference,
    MessageActivityInput,
    SentActivity,
)
from microsoft_teams.common import Client

from .http_stream import HttpStream
from .plugins.streamer import StreamerProtocol

logger = logging.getLogger(__name__)


class ActivitySender:
    """
    Handles sending activities to the Bot Framework.
    Separate from transport concerns (HTTP, WebSocket, etc.)
    """

    def __init__(self, client: Client):
        """
        Initialize ActivitySender.

        Args:
            client: HTTP client with token provider configured
        """
        self._client = client

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

        is_targeted = (
            isinstance(activity, MessageActivityInput)
            and activity.recipient is not None
            and activity.recipient.is_targeted is True
        )
        is_update = hasattr(activity, "id") and activity.id
        activities = api.conversations.activities(ref.conversation.id)

        if is_update:
            activity_id = cast(str, activity.id)
            if is_targeted:
                res = await activities.update_targeted(activity_id, activity)
            else:
                res = await activities.update(activity_id, activity)
            return SentActivity.merge(activity, res)

        if is_targeted:
            res = await activities.create_targeted(activity)
        else:
            res = await activities.create(activity)
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
        return HttpStream(api, ref)
