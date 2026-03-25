"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal, Optional

from microsoft_teams.common.experimental import experimental

from ..custom_base_model import CustomBaseModel


@experimental("ExperimentalTeamsQuotedReplies")
class QuotedReplyData(CustomBaseModel):
    """Data for a quoted reply entity

    .. warning:: Preview
        This API is in preview and may change in the future.
        Diagnostic: ExperimentalTeamsQuotedReplies
    """

    message_id: str
    "ID of the message being quoted"

    sender_id: Optional[str] = None
    "ID of the sender of the quoted message"

    sender_name: Optional[str] = None
    "Name of the sender of the quoted message"

    preview: Optional[str] = None
    "Preview text of the quoted message"

    time: Optional[str] = None
    "Timestamp of the quoted message (IC3 epoch value, e.g. '1772050244572'). Inbound only."

    is_reply_deleted: Optional[bool] = None
    "Whether the quoted reply has been deleted"

    validated_message_reference: Optional[bool] = None
    "Whether the message reference has been validated"


@experimental("ExperimentalTeamsQuotedReplies")
class QuotedReplyEntity(CustomBaseModel):
    """Entity containing quoted reply information

    .. warning:: Preview
        This API is in preview and may change in the future.
        Diagnostic: ExperimentalTeamsQuotedReplies
    """

    type: Literal["quotedReply"] = "quotedReply"
    "Type identifier for quoted reply"

    quoted_reply: QuotedReplyData
    "The quoted reply data"
