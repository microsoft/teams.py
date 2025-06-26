"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Dict, Optional, Protocol


class PluginProtocol(Protocol):
    """Protocol for Teams app plugins."""

    async def on_start(self, port: int) -> None:
        """Called when the app starts."""
        ...

    async def on_stop(self) -> None:
        """Called when the app stops."""
        ...

    def on_error(self, error: Exception, activity_id: Optional[str] = None) -> None:
        """Called by the App when an error occurs."""
        ...

    def on_activity_response(self, activity_id: str, response_data: Dict[str, Any]) -> None:
        """Called by the App when an activity response is sent."""
        ...
