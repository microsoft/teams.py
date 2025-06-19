"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from enum import Enum


class MessageReactionType(str, Enum):
    """Enum for message reaction types."""

    LIKE = "like"
    HEART = "heart"
    LAUGH = "laugh"
    SURPRISED = "surprised"
    SAD = "sad"
    ANGRY = "angry"
    PLUS_ONE = "plusOne"
    UNKNOWN = "unknown"

    @classmethod
    def _missing_(cls, value: object) -> "MessageReactionType":
        """Return unknown value for missing enum values."""
        return cls.UNKNOWN
