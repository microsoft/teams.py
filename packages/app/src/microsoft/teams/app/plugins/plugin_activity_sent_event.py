"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from microsoft.teams.api.models import ConversationReference, Resource

from .sender import SenderProtocol


class PluginActivitySentEvent(ConversationReference):
    """Event emitted by a plugin when an activity is sent."""

    sender: SenderProtocol
    """The sender of the activity"""

    activity: Resource
    """The sent activity"""
