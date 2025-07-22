"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Callable, Dict, NamedTuple, Optional, Type

from microsoft.teams.api.activities import (
    ActivityBase,
    ConversationUpdateActivity,
    EndOfConversationActivity,
    EventActivity,
    HandoffActivity,
    InstallUpdateActivity,
    InvokeActivity,
    MessageActivity,
    MessageDeleteActivity,
    MessageReactionActivity,
    MessageUpdateActivity,
    TraceActivity,
    TypingActivity,
)
from microsoft.teams.api.activities.command import (
    CommandResultActivity,
    CommandSendActivity,
)

RouteSelector = Callable[[ActivityBase], bool]


class ActivityConfig(NamedTuple):
    """Configuration for an activity handler."""

    name: str
    """The activity type string (e.g., 'message', 'invoke')."""

    method_name: str
    """The generated method name (e.g., 'onMessage', 'onInvoke')."""

    input_model: Type[ActivityBase]
    """The input activity class type."""

    selector: RouteSelector
    """Function that determines if this route matches the given activity."""

    output_model: Optional[Type] = None
    """The output model class type. None if no specific output type."""

    type_name: Optional[str] = None
    """Override for the type name in generated code. If None, uses input_model.__name__."""


ACTIVITY_ROUTES: Dict[str, ActivityConfig] = {
    # Message Activities
    "message": ActivityConfig(
        name="message",
        method_name="onMessage",
        input_model=MessageActivity,
        selector=lambda activity: activity.type == "message",
        output_model=None,
        type_name="MessageActivity",
    ),
    "messageDelete": ActivityConfig(
        name="messageDelete",
        method_name="onMessageDelete",
        input_model=MessageDeleteActivity,
        selector=lambda activity: activity.type == "messageDelete",
        output_model=None,
        type_name="MessageDeleteActivity",
    ),
    "messageReaction": ActivityConfig(
        name="messageReaction",
        method_name="onMessageReaction",
        input_model=MessageReactionActivity,
        selector=lambda activity: activity.type == "messageReaction",
        output_model=None,
        type_name="MessageReactionActivity",
    ),
    "messageUpdate": ActivityConfig(
        name="messageUpdate",
        method_name="onMessageUpdate",
        input_model=MessageUpdateActivity,
        selector=lambda activity: activity.type == "messageUpdate",
        output_model=None,
        type_name="MessageUpdateActivity",
    ),
    # Command Activities
    "command": ActivityConfig(
        name="command",
        method_name="onCommand",
        input_model=CommandSendActivity,
        selector=lambda activity: activity.type == "command",
        output_model=None,
        type_name="CommandSendActivity",
    ),
    "commandResult": ActivityConfig(
        name="commandResult",
        method_name="onCommandResult",
        input_model=CommandResultActivity,
        selector=lambda activity: activity.type == "commandResult",
        output_model=None,
        type_name="CommandResultActivity",
    ),
    # Conversation Activities
    "conversationUpdate": ActivityConfig(
        name="conversationUpdate",
        method_name="onConversationUpdate",
        input_model=ConversationUpdateActivity,
        selector=lambda activity: activity.type == "conversationUpdate",
        output_model=None,
        type_name="ConversationUpdateActivity",
    ),
    "endOfConversation": ActivityConfig(
        name="endOfConversation",
        method_name="onEndOfConversation",
        input_model=EndOfConversationActivity,
        selector=lambda activity: activity.type == "endOfConversation",
        output_model=None,
        type_name="EndOfConversationActivity",
    ),
    # Complex Union Activities (discriminated by sub-fields)
    "event": ActivityConfig(
        name="event",
        method_name="onEvent",
        input_model=EventActivity,
        selector=lambda activity: activity.type == "event",
        output_model=None,
        type_name="EventActivity",
    ),
    "invoke": ActivityConfig(
        name="invoke",
        method_name="onInvoke",
        input_model=InvokeActivity,
        selector=lambda activity: activity.type == "invoke",
        output_model=None,
        type_name="InvokeActivity",
    ),
    "installationUpdate": ActivityConfig(
        name="installationUpdate",
        method_name="onInstallationUpdate",
        input_model=InstallUpdateActivity,
        selector=lambda activity: activity.type == "installationUpdate",
        output_model=None,
        type_name="InstallUpdateActivity",
    ),
    # Other Core Activities
    "typing": ActivityConfig(
        name="typing",
        method_name="onTyping",
        input_model=TypingActivity,
        selector=lambda activity: activity.type == "typing",
        output_model=None,
        type_name="TypingActivity",
    ),
    "trace": ActivityConfig(
        name="trace",
        method_name="onTrace",
        input_model=TraceActivity,
        selector=lambda activity: activity.type == "trace",
        output_model=None,
        type_name="TraceActivity",
    ),
    "handoff": ActivityConfig(
        name="handoff",
        method_name="onHandoff",
        input_model=HandoffActivity,
        selector=lambda activity: activity.type == "handoff",
        output_model=None,
        type_name="HandoffActivity",
    ),
    # Generic Activity Handler (catch-all)
    "activity": ActivityConfig(
        name="activity",
        method_name="onActivity",
        input_model=ActivityBase,
        selector=lambda activity: True,
        output_model=None,
        type_name="ActivityBase",
    ),
}
