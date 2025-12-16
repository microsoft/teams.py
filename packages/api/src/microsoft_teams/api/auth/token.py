"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional, Protocol, runtime_checkable

from .caller import CallerType


@runtime_checkable
class TokenProtocol(Protocol):
    """Any authorized token."""

    @property
    def app_id(self) -> str:
        """The app id."""
        ...

    @property
    def app_display_name(self) -> Optional[str]:
        """The app display name."""
        ...

    @property
    def tenant_id(self) -> Optional[str]:
        """The tenant id."""
        ...

    @property
    def service_url(self) -> str:
        """The service url to send responses to."""
        ...

    @property
    def from_(self) -> CallerType:
        """Where the activity originated from."""
        ...

    @property
    def from_id(self) -> str:
        """The id of the activity sender."""
        ...

    @property
    def expiration(self) -> Optional[int]:
        """The expiration of the token since epoch in milliseconds."""
        ...

    def is_expired(self, buffer_ms: int = 5 * 60 * 1000) -> bool:
        """
        Check if the token is expired.

        Args:
            buffer_ms: Buffer time in milliseconds (default 5 minutes).

        Returns:
            True if the token is expired, False otherwise.
        """
        ...

    def __str__(self) -> str:
        """String form of the token."""
        ...
