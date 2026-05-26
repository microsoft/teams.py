"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal, Optional

from ..custom_base_model import CustomBaseModel


class QuotedReplyEntity(CustomBaseModel):
    """Teams quoted-reply metadata attached to a reply activity."""

    type: Literal["quotedReply"] = "quotedReply"
    message_id: Optional[str] = None
