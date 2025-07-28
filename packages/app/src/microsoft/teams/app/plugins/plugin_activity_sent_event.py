"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import TYPE_CHECKING

from microsoft.teams.api.models import ConversationReference, Resource

if TYPE_CHECKING:
    from .sender import Sender


class PluginActivitySentEvent(ConversationReference):
    """Event emitted by a plugin when an activity is sent."""

    sender: "Sender"
    """The sender of the activity"""

    activity: Resource
    """The sent activity"""
