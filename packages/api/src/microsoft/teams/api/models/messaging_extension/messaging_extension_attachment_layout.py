"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from enum import Enum


class MessagingExtensionAttachmentLayout(str, Enum):
    """Enum for messaging extension attachment layout types."""

    LIST = "list"
    GRID = "grid"
