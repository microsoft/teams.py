"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import TYPE_CHECKING, Any, NamedTuple, Optional

from microsoft.teams.api import Activity
from microsoft.teams.api.models import ConversationReference, InvokeResponse

if TYPE_CHECKING:
    from .sender import Sender


class PluginActivityResponseEvent(NamedTuple):
    """Event emitted by a plugin before an activity response is sent"""

    conversation_ref: ConversationReference
    """The conversation reference for the activity"""

    sender: "Sender"
    """The sender"""

    activity: Activity
    """The inbound request activity payload"""

    response: Optional[InvokeResponse[Any]]
    """The response"""
