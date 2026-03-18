"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal, Optional

from ..custom_base_model import CustomBaseModel


class QuotedReplyData(CustomBaseModel):
    """Data for a quoted reply entity"""

    message_id: str
    "ID of the message being quoted"

    sender_id: Optional[str] = None
    "ID of the sender of the quoted message"

    sender_name: Optional[str] = None
    "Name of the sender of the quoted message"

    preview: Optional[str] = None
    "Preview text of the quoted message"

    time: Optional[str] = None
    "Timestamp of the quoted message"

    is_reply_deleted: Optional[bool] = None
    "Whether the quoted reply has been deleted"

    validated_message_reference: Optional[bool] = None
    "Whether the message reference has been validated"


class QuotedReplyEntity(CustomBaseModel):
    """Entity containing quoted reply information"""

    type: Literal["quotedReply"] = "quotedReply"
    "Type identifier for quoted reply"

    quoted_reply: QuotedReplyData
    "The quoted reply data"
