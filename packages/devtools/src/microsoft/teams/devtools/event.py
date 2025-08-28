"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from datetime import datetime
from typing import Annotated, Any, Optional, Union

from microsoft.teams.api.models import ConversationAccount, CustomBaseModel
from pydantic import Field


class DevToolsEvent(CustomBaseModel):
    id: str
    type: str
    body: Any
    sent_at: datetime


class DevToolsActivityReceivedEvent(DevToolsEvent):
    type: str = "activity.received"
    chat: ConversationAccount


class DevToolsActivitySendingEvent(DevToolsEvent):
    type: str = "activity.sending"
    chat: ConversationAccount


class DevToolsActivitySentEvent(DevToolsEvent):
    type: str = "activity.sent"
    chat: ConversationAccount


class DevToolsActivityErrorEvent(DevToolsEvent):
    type: str = "activity.error"
    chat: ConversationAccount
    error: Optional[Any] = None


DevToolsActivityEvent = Annotated[
    Union[
        DevToolsActivityReceivedEvent
        | DevToolsActivitySendingEvent
        | DevToolsActivitySentEvent
        | DevToolsActivityErrorEvent
    ],
    Field(discriminator="type"),
]
