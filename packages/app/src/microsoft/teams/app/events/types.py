"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional, Union

from microsoft.teams.api import (
    Activity,
    ConversationReference,
    InvokeResponse,
    SentActivity,
    SignInTokenExchangeInvokeActivity,
    SignInVerifyStateInvokeActivity,
    TokenProtocol,
    TokenResponse,
)

from ..plugins import PluginBase, Sender
from ..routing import ActivityContext


@dataclass
class ActivityEvent:
    """Event emitted when an activity is processed."""

    activity: Activity
    sender: Sender
    token: TokenProtocol

    def __repr__(self) -> str:
        return f"ActivityEvent(activity={self.activity}, token={self.token}, sender={self.sender})"


@dataclass
class ErrorEvent:
    """Event emitted when an error occurs."""

    error: Exception
    context: Optional[Dict[str, Any]] = None
    activity: Optional[Activity] = None
    sender: Optional[PluginBase] = None

    def __post_init__(self) -> None:
        if self.context is None:
            self.context = {}

    def __repr__(self) -> str:
        return f"ErrorEvent(error={self.error}, context={self.context}, activity={self.activity}, sender={self.sender})"


@dataclass
class ActivitySentEvent:
    """Event emitted by a plugin when an activity is sent."""

    sender: Sender
    activity: SentActivity
    conversation_ref: ConversationReference

    def __repr__(self) -> str:
        return (
            f"ActivitySentEvent(sender={self.sender}, activity={self.activity}, "
            + f"conversation_ref={self.conversation_ref})"
        )


@dataclass
class ActivityResponseEvent:
    """Event emitted by a plugin before an invoke response is returned."""

    activity: Activity
    response: InvokeResponse[Any]
    conversation_ref: ConversationReference

    def __repr__(self) -> str:
        return (
            f"ActivityResponseEvent(activity={self.activity}, response={self.response}, "
            + f"conversation_ref={self.conversation_ref})"
        )


@dataclass
class StartEvent:
    """Event emitted when the app starts."""

    port: int

    def __repr__(self) -> str:
        return f"StartEvent(port={self.port})"


@dataclass
class StopEvent:
    """Event emitted when the app stops."""

    def __repr__(self) -> str:
        return "StopEvent()"


@dataclass
class SignInEvent:
    activity_ctx: Union[
        ActivityContext[SignInVerifyStateInvokeActivity],
        ActivityContext[SignInTokenExchangeInvokeActivity],
    ]
    token_response: TokenResponse
