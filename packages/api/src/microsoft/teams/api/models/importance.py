from enum import Enum


class Importance(str, Enum):
    """Enum for user identity types."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
