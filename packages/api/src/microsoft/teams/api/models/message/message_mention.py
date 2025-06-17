"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from ..custom_base_model import CustomBaseModel
from .message_from import MessageFrom


class MessageMention(CustomBaseModel):
    """
    Represents the entity that was mentioned in the message.
    """

    id: int
    "The id of the mentioned entity."

    mention_text: Optional[str] = None
    "The plaintext display name of the mentioned entity."

    mentioned: Optional[MessageFrom] = None
    "Provides more details on the mentioned entity."
