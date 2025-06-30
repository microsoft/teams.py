"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Protocol


class EventProtocol(Protocol):
    """Protocol for event objects in the Teams app system."""

    def __repr__(self) -> str:
        """String representation of the event."""
        ...
