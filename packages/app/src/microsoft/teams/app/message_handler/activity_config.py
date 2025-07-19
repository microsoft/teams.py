"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import List, NamedTuple, Optional, Type

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


class ActivityConfig(NamedTuple):
    """Configuration for an activity handler."""

    name: str
    """The activity type string (e.g., 'message', 'invoke')."""

    method_name: str
    """The generated method name (e.g., 'onMessage', 'onInvoke')."""

    input_model: Type[ActivityBase]
    """The input activity class type."""

    output_model: Optional[Type] = None
    """The output model class type. None if no specific output type."""

    type_name: Optional[str] = None
    """Override for the type name in generated code. If None, uses input_model.__name__."""


ACTIVITY_ROUTES: List[ActivityConfig] = [
    # Message Activities
    ActivityConfig(
        name="message",
        method_name="onMessage",
        input_model=MessageActivity,
        output_model=None,
        type_name="MessageActivity",
    ),
    ActivityConfig(
        name="messageDelete",
        method_name="onMessageDelete",
        input_model=MessageDeleteActivity,
        output_model=None,
        type_name="MessageDeleteActivity",
    ),
    ActivityConfig(
        name="messageReaction",
        method_name="onMessageReaction",
        input_model=MessageReactionActivity,
        output_model=None,
        type_name="MessageReactionActivity",
    ),
    ActivityConfig(
        name="messageUpdate",
        method_name="onMessageUpdate",
        input_model=MessageUpdateActivity,
        output_model=None,
        type_name="MessageUpdateActivity",
    ),
    # Command Activities
    ActivityConfig(
        name="command",
        method_name="onCommand",
        input_model=CommandSendActivity,
        output_model=None,
        type_name="CommandSendActivity",
    ),
    ActivityConfig(
        name="commandResult",
        method_name="onCommandResult",
        input_model=CommandResultActivity,
        output_model=None,
        type_name="CommandResultActivity",
    ),
    # Conversation Activities
    ActivityConfig(
        name="conversationUpdate",
        method_name="onConversationUpdate",
        input_model=ConversationUpdateActivity,
        output_model=None,
        type_name="ConversationUpdateActivity",
    ),
    ActivityConfig(
        name="endOfConversation",
        method_name="onEndOfConversation",
        input_model=EndOfConversationActivity,
        output_model=None,
        type_name="EndOfConversationActivity",
    ),
    # Complex Union Activities (discriminated by sub-fields)
    ActivityConfig(
        name="event",
        method_name="onEvent",
        input_model=EventActivity,
        output_model=None,
        type_name="EventActivity",
    ),
    ActivityConfig(
        name="invoke",
        method_name="onInvoke",
        input_model=InvokeActivity,
        output_model=None,
        type_name="InvokeActivity",
    ),
    ActivityConfig(
        name="installationUpdate",
        method_name="onInstallationUpdate",
        input_model=InstallUpdateActivity,
        output_model=None,
        type_name="InstallUpdateActivity",
    ),
    # Other Core Activities
    ActivityConfig(
        name="typing",
        method_name="onTyping",
        input_model=TypingActivity,
        output_model=None,
        type_name="TypingActivity",
    ),
    ActivityConfig(
        name="trace",
        method_name="onTrace",
        input_model=TraceActivity,
        output_model=None,
        type_name="TraceActivity",
    ),
    ActivityConfig(
        name="handoff",
        method_name="onHandoff",
        input_model=HandoffActivity,
        output_model=None,
        type_name="HandoffActivity",
    ),
    # Generic Activity Handler (catch-all)
    ActivityConfig(
        name="activity",
        method_name="onActivity",
        input_model=ActivityBase,
        output_model=None,
        type_name="ActivityBase",
    ),
]
