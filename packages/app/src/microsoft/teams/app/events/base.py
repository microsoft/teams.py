"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Dict, Optional, Protocol


class EventProtocol(Protocol):
    """Protocol for event objects in the Teams app system."""

    data: Dict[str, Any]

    def __repr__(self) -> str:
        """String representation of the event."""
        ...


class BaseEvent:
    """Base implementation for events in the Teams app system."""

    def __init__(self, data: Optional[Dict[str, Any]] = None):
        """
        Initialize base event.

        Args:
            data: Optional event data payload
        """
        self.data = data or {}

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(data={self.data})"
