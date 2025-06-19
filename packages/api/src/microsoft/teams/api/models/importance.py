"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from enum import Enum


class Importance(str, Enum):
    """Enum for user identity types."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    UNKNOWN = "unknown"

    @classmethod
    def _missing_(cls, value: object) -> "Importance":
        """Return unknown value for missing enum values."""
        return cls.UNKNOWN
