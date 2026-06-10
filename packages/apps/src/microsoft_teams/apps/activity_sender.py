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

    def __init__(
        self,
        client: Client,
        stream_min_send_interval: float = 1.0,
        stream_coalesce_informative_updates: bool = False,
    ):
        """
        Initialize ActivitySender.

        Args:
            client: HTTP client with token provider configured
            stream_min_send_interval: Minimum seconds between sends on streams created by
                create_stream() (Teams limits streaming to 1 req/s). Set 0 to disable pacing.
            stream_coalesce_informative_updates: When True, a burst of informative updates in one
                flush collapses to the latest one instead of pacing out every update.
        """
        self._client = client
        self._stream_min_send_interval = stream_min_send_interval
        self._stream_coalesce_informative_updates = stream_coalesce_informative_updates

    async def send(self, activity: ActivityParams, ref: ConversationReference) -> SentActivity:
        """
        Send an activity to the Bot Framework.

        Args:
            activity: The activity to send
            ref: The conversation reference

        Returns:
            The sent activity with id and other server-populated fields
        """
        is_targeted = (
            isinstance(activity, MessageActivityInput)
            and activity.recipient is not None
            and activity.recipient.is_targeted is True
        )

        if is_targeted and ref.conversation.conversation_type == "personal":
            raise ValueError("Targeted messages are not supported in 1:1 (personal) chats.")

        # Create API client for this conversation's service URL
        api = ApiClient(service_url=ref.service_url, options=self._client)

        # Merge activity with conversation reference
        activity.from_ = ref.bot
        activity.conversation = ref.conversation

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
        return HttpStream(
            api,
            ref,
            min_send_interval=self._stream_min_send_interval,
            coalesce_informative_updates=self._stream_coalesce_informative_updates,
        )
