"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import NamedTuple

from microsoft_teams.api.activities import SentActivity
from microsoft_teams.api.models import ConversationReference


class PluginActivitySentEvent(NamedTuple):
    """Event emitted when an activity is sent."""

    activity: SentActivity
    """The sent activity"""

    conversation_ref: ConversationReference
    """The conversation reference for the activity"""
