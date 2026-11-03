"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from __future__ import annotations

from typing import Any, List, Literal, Optional, Union

from ...models.activity import Activity as ActivityBase
from ..custom_base_model import CustomBaseModel
from ..message import Message
from ..tab import TabEntityContext

MessagingExtensionCommandContext = Union[Literal["message", "compose", "commandbox"], str]
BotMessagePreviewAction = Union[Literal["edit", "send"], str]


class TaskModuleRequestContext(CustomBaseModel):
    """
    Current user context, i.e., the current theme
    """

    theme: Optional[str] = None
    "Theme context"


class TaskModuleRequest(CustomBaseModel):
    """
    Task module invoke request value payload
    """

    data: Optional[Any] = None
    "User input data. Free payload with key-value pairs."

    context: Optional[TaskModuleRequestContext] = None
    "Current user context, i.e., the current theme"

    tab_context: Optional[TabEntityContext] = None
    "Tab request context."


class MessagingExtensionAction(TaskModuleRequest):
    """
    Messaging extension action
    """

    command_id: Optional[str] = None
    "Id of the command assigned by Bot"

    command_context: MessagingExtensionCommandContext
    "The context from which the command originates."

    bot_message_preview_action: Optional[BotMessagePreviewAction] = None
    "Bot message preview action taken by user."

    bot_activity_preview: Optional[List[ActivityBase]] = None
    "Bot activity preview"

    message_payload: Optional[Message] = None
    "Message content sent as part of the command request."
