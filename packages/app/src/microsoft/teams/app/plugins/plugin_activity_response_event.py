"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any

from microsoft.teams.api.activities import Activity
from microsoft.teams.api.models import ConversationReference, InvokeResponse

from .sender import SenderProtocol


class PluginActivityResponseEvent(ConversationReference):
    """Event emitted by a plugin before an activity response is sent"""

    sender: SenderProtocol
    """The sender"""

    activity: Activity
    """The inbound request activity payload"""

    response: InvokeResponse[Any]
    """The response"""
