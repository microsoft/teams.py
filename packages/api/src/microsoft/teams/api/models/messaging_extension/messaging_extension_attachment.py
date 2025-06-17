from typing import Optional

from ..attachment import Attachment


class MessagingExtensionAttachment(Attachment):
    """
    Messaging extension attachment.
    """

    preview: Optional[Attachment] = None
    "Preview attachment"
