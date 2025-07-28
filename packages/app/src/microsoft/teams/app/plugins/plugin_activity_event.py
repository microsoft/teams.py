"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import TYPE_CHECKING

from microsoft.teams.api import Activity, TokenProtocol
from microsoft.teams.api.models.conversation import ConversationReference

if TYPE_CHECKING:
    from .sender import Sender


class PluginActivityEvent(ConversationReference):
    """Event emitted by a plugin when an activity is received."""

    sender: "Sender"
    """The sender"""

    token: TokenProtocol
    """Inbound request token"""

    activity: Activity
    """Inbound request activity payload"""
