"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import TYPE_CHECKING, NamedTuple, Optional

from microsoft.teams.api import Activity, ConversationReference, TokenProtocol

if TYPE_CHECKING:
    from .sender import Sender


class PluginActivityEvent(NamedTuple):
    """Event emitted by a plugin when an activity is received."""

    token: TokenProtocol
    """Inbound request token"""

    activity: Activity
    """Inbound request activity payload"""

    conversation_ref: ConversationReference
    """The conversation reference for the activity"""

    sender: Optional["Sender"] = None
    """The sender"""
