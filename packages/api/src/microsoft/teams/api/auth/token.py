"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from abc import ABC, abstractmethod
from typing import Optional

from .caller import CallerType


class IToken(ABC):
    """Any authorized token."""

    @property
    @abstractmethod
    def app_id(self) -> str:
        """The app id."""
        pass

    @property
    @abstractmethod
    def app_display_name(self) -> Optional[str]:
        """The app display name."""
        pass

    @property
    @abstractmethod
    def tenant_id(self) -> Optional[str]:
        """The tenant id."""
        pass

    @property
    @abstractmethod
    def service_url(self) -> str:
        """The service url to send responses to."""
        pass

    @property
    @abstractmethod
    def from_(self) -> CallerType:
        """Where the activity originated from."""
        pass

    @property
    @abstractmethod
    def from_id(self) -> str:
        """The id of the activity sender."""
        pass

    @property
    @abstractmethod
    def expiration(self) -> Optional[int]:
        """The expiration of the token since epoch in milliseconds."""
        pass

    @abstractmethod
    def is_expired(self, buffer_ms: int = 5 * 60 * 1000) -> bool:
        """
        Check if the token is expired.

        Args:
            buffer_ms: Buffer time in milliseconds (default 5 minutes).

        Returns:
            True if the token is expired, False otherwise.
        """
        pass

    @abstractmethod
    def __str__(self) -> str:
        """String form of the token."""
        pass
