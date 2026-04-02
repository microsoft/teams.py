"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional, Union

from microsoft_teams.api import (
    Activity,
    ConversationReference,
    InvokeResponse,
    SentActivity,
    SignInTokenExchangeInvokeActivity,
    SignInVerifyStateInvokeActivity,
    TokenProtocol,
    TokenResponse,
)
from pydantic import BaseModel, ConfigDict

from ..routing import ActivityContext


class CoreActivity(BaseModel):
    """
    Core activity fields that all transports need to know about.
    Extensible for protocol-specific fields via extra="allow".
    """

    model_config = ConfigDict(extra="allow")

    service_url: Optional[str] = None
    """Service URL for routing"""

    id: Optional[str] = None
    """Activity ID for correlation"""

    type: Optional[str] = None
    """Activity type for basic routing"""


@dataclass
class ActivityEvent:
    """Event emitted when an activity is processed."""

    body: CoreActivity
    token: TokenProtocol

    def __repr__(self) -> str:
        return f"ActivityEvent(body={self.body}, token={self.token})"


@dataclass
class ErrorEvent:
    """Event emitted when an error occurs."""

    error: Exception
    context: Optional[Dict[str, Any]] = None
    activity: Optional[Activity] = None

    def __post_init__(self) -> None:
        if self.context is None:
            self.context = {}

    def __repr__(self) -> str:
        return f"ErrorEvent(error={self.error}, context={self.context}, activity={self.activity})"


@dataclass
class ActivitySentEvent:
    """Event emitted when an activity is sent."""

    activity: SentActivity
    conversation_ref: ConversationReference

    def __repr__(self) -> str:
        return f"ActivitySentEvent(activity={self.activity}, conversation_ref={self.conversation_ref})"


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
