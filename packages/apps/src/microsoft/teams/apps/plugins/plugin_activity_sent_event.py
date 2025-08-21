"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import TYPE_CHECKING, NamedTuple

from microsoft.teams.api.activities import SentActivity
from microsoft.teams.api.models import ConversationReference

if TYPE_CHECKING:
    from .sender import Sender


class PluginActivitySentEvent(NamedTuple):
    """Event emitted by a plugin when an activity is sent."""

    sender: "Sender"
    """The sender of the activity"""

    activity: SentActivity
    """The sent activity"""

    conversation_ref: ConversationReference
    """The conversation reference for the activity"""
