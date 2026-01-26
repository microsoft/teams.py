"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, NamedTuple, Optional

from microsoft_teams.api import Activity, ConversationReference, InvokeResponse


class PluginActivityResponseEvent(NamedTuple):
    """Event emitted before an activity response is sent"""

    activity: Activity
    """The inbound request activity payload"""

    conversation_ref: ConversationReference
    """The conversation reference for the activity"""

    response: Optional[InvokeResponse[Any]]
    """The response"""
