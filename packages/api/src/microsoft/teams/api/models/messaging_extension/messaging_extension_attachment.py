"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from ..attachment import Attachment


class MessagingExtensionAttachment(Attachment):
    """
    Messaging extension attachment.
    """

    preview: Optional[Attachment] = None
    "Preview attachment"
