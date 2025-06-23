"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Dict, Optional

from microsoft.teams.api import Activity, TokenProtocol

from .base import BaseEvent


class ActivityEvent(BaseEvent):
    """Event emitted when an activity is processed."""

    def __init__(self, activity: Activity, **kwargs: Any):
        """
        Initialize activity event.

        Args:
            activity: The Teams activity being processed
            **kwargs: Additional event data
        """
        data = {"activity": activity, **kwargs}
        super().__init__(data)

    @property
    def activity(self) -> Activity:
        """The Teams activity associated with this event."""
        return self.data["activity"]


class ErrorEvent(BaseEvent):
    """Event emitted when an error occurs."""

    def __init__(self, error: Exception, context: Optional[Dict[str, Any]] = None, **kwargs: Any):
        """
        Initialize error event.

        Args:
            error: The exception that occurred
            context: Optional context information about where the error occurred
            **kwargs: Additional event data
        """
        data = {"error": error, "context": context or {}, **kwargs}
        super().__init__(data)

    @property
    def error(self) -> Exception:
        """The exception associated with this event."""
        return self.data["error"]

    @property
    def context(self) -> Dict[str, Any]:
        """Context information about the error."""
        return self.data["context"]


class StartEvent(BaseEvent):
    """Event emitted when the app starts."""

    def __init__(self, port: int, **kwargs: Any):
        """
        Initialize start event.

        Args:
            port: Port the app is running on
            **kwargs: Additional event data
        """
        data = {"port": port, **kwargs}
        super().__init__(data)

    @property
    def port(self) -> int:
        """Port the app is running on."""
        return self.data["port"]


class StopEvent(BaseEvent):
    """Event emitted when the app stops."""

    def __init__(self, **kwargs: Any):
        """
        Initialize stop event.

        Args:
            **kwargs: Additional event data
        """
        super().__init__(kwargs)


class TokenEvent(BaseEvent):
    """Event emitted when authentication tokens are refreshed."""

    def __init__(self, token_type: str, token: Optional[TokenProtocol] = None, **kwargs: Any):
        """
        Initialize token event.

        Args:
            token_type: Type of token ("bot" or "graph")
            token: The refreshed token (optional for privacy)
            **kwargs: Additional event data
        """
        data = {"token_type": token_type, "token": token, **kwargs}
        super().__init__(data)

    @property
    def token_type(self) -> str:
        """Type of token that was refreshed."""
        return self.data["token_type"]

    @property
    def token(self) -> Optional[TokenProtocol]:
        """The refreshed token (may be None for privacy)."""
        return self.data.get("token")
