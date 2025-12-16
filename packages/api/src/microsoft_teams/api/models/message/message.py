"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import List, Literal, Optional

from ..attachment import Attachment
from ..custom_base_model import CustomBaseModel
from ..importance import Importance
from .message_body import MessageBody
from .message_from import MessageFrom
from .message_mention import MessageMention
from .message_reaction import MessageReaction


class Message(CustomBaseModel):
    """
    Represents the individual message within a chat or channel where a message
    actions is taken.
    """

    id: str
    "Unique id of the message."

    reply_to_id: Optional[str] = None
    "Id of the parent/root message of the thread."

    message_type: Optional[Literal["message"]] = "message"
    "Type of message - automatically set to message."

    created_date_time: Optional[str] = None
    "Timestamp of when the message was created."

    last_modified_date_time: Optional[str] = None
    "Timestamp of when the message was edited or updated."

    deleted: Optional[bool] = None
    "Indicates whether a message has been soft deleted."

    subject: Optional[str] = None
    "Subject line of the message."

    summary: Optional[str] = None
    "Summary text of the message that could be used for notifications."

    importance: Optional[Importance] = None
    "The importance of the message."

    locale: Optional[str] = None
    "Locale of the message set by the client."

    link_to_message: Optional[str] = None
    "Link back to the message."

    from_: Optional[MessageFrom] = None
    "Sender of the message."

    body: Optional[MessageBody] = None
    "Plaintext/HTML representation of the content of the message."

    attachment_layout: Optional[str] = None
    "How the attachment(s) are displayed in the message."

    attachments: Optional[List[Attachment]] = None
    "Attachments in the message - card, image, file, etc."

    mentions: Optional[List[MessageMention]] = None
    "List of entities mentioned in the message."

    reactions: Optional[List[MessageReaction]] = None
    "Reactions for the message."
