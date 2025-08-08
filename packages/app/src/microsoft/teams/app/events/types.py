"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, Optional, Union

from microsoft.teams.api import (
    Activity,
    SignInTokenExchangeInvokeActivity,
    SignInVerifyStateInvokeActivity,
    TokenResponse,
)

if TYPE_CHECKING:
    from ..routing import ActivityContext


@dataclass
class ActivityEvent:
    """Event emitted when an activity is processed."""

    activity: Activity

    def __repr__(self) -> str:
        return f"ActivityEvent(activity={self.activity})"


@dataclass
class ErrorEvent:
    """Event emitted when an error occurs."""

    error: Exception
    context: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        if self.context is None:
            self.context = {}

    def __repr__(self) -> str:
        return f"ErrorEvent(error={self.error}, context={self.context})"


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
        "ActivityContext[SignInVerifyStateInvokeActivity]",
        "ActivityContext[SignInTokenExchangeInvokeActivity]",
    ]
    token_response: TokenResponse
