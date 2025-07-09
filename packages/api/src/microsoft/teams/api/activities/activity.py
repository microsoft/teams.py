"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from ..activity_params import ActivityParams
from ..models import Account, ChannelID, ConversationAccount


class Activity(ActivityParams):
    """Base class for all activities."""

    id: str
    """Contains an ID that uniquely identifies the activity on the channel."""

    channel_id: ChannelID
    """Contains an ID that uniquely identifies the channel. Set by the channel."""

    from_: Account
    """Identifies the sender of the message."""

    conversation: ConversationAccount
    """Identifies the conversation to which the activity belongs."""

    recipient: Account
