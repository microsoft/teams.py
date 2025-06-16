from enum import Enum


class AttachmentLayout(str, Enum):
    """Enum for attachment layout types."""

    LIST = "list"
    CAROUSEL = "carousel"
