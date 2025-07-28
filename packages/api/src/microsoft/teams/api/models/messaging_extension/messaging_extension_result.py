"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from __future__ import annotations

from typing import List, Optional

from ...models.activity import Activity as ActivityBase
from ..attachment.attachment_layout import AttachmentLayout
from ..custom_base_model import CustomBaseModel
from .messaging_extension_attachment import MessagingExtensionAttachment
from .messaging_extension_result_type import MessagingExtensionResultType
from .messaging_extension_suggested_action import MessagingExtensionSuggestedAction


class MessagingExtensionResult(CustomBaseModel):
    """
    Messaging extension result
    """

    attachment_layout: Optional[AttachmentLayout] = None
    "Hint for how to deal with multiple attachments."

    type: Optional[MessagingExtensionResultType] = None
    "The type of the result."

    attachments: Optional[List[MessagingExtensionAttachment]] = None
    "(Only when type is result) Attachments"

    suggested_actions: Optional[MessagingExtensionSuggestedAction] = None
    "Suggested actions for the extension"

    text: Optional[str] = None
    "(Only when type is message) Text"

    activity_preview: Optional[ActivityBase] = None
    "(Only when type is botMessagePreview) Message activity to preview"
