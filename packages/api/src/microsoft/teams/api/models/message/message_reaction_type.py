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
