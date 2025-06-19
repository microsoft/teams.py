"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from enum import Enum


class AttachmentLayout(str, Enum):
    """Enum for attachment layout types."""

    LIST = "list"
    CAROUSEL = "carousel"
    UNKNOWN = "unknown"

    @classmethod
    def _missing_(cls, value: object) -> "AttachmentLayout":
        """Return unknown value for missing enum values."""
        return cls.UNKNOWN
