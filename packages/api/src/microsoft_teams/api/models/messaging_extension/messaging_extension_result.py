"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from __future__ import annotations

from typing import Annotated, List, Optional, Union

from pydantic import Field

from ...models.activity import Activity as ActivityBase
from ..custom_base_model import CustomBaseModel
from .messaging_extension_attachment import MessagingExtensionAttachment
from .messaging_extension_attachment_layout import MessagingExtensionAttachmentLayout
from .messaging_extension_result_type import MessagingExtensionResultType
from .messaging_extension_suggested_action import MessagingExtensionSuggestedAction


class MessagingExtensionResult(CustomBaseModel):
    """
    Messaging extension result
    """

    attachment_layout: Optional[
        Annotated[Union[MessagingExtensionAttachmentLayout, str], Field(union_mode="left_to_right")]
    ] = None
    "Hint for how to deal with multiple attachments."

    type: Optional[Annotated[Union[MessagingExtensionResultType, str], Field(union_mode="left_to_right")]] = None
    "The type of the result."

    attachments: Optional[List[MessagingExtensionAttachment]] = None
    "(Only when type is result) Attachments"

    suggested_actions: Optional[MessagingExtensionSuggestedAction] = None
    "Suggested actions for the extension"

    text: Optional[str] = None
    "(Only when type is message) Text"

    activity_preview: Optional[ActivityBase] = None
    "(Only when type is botMessagePreview) Message activity to preview"
