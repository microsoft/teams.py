"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from ..custom_base_model import CustomBaseModel
from .message_reaction_type import MessageReactionType
from .message_user import MessageUser


class MessageReaction(CustomBaseModel):
    """
    Represents a reaction to a message.
    """

    type: MessageReactionType
    "The type of reaction given to the message."

    created_date_time: Optional[str] = None
    "Timestamp of when the user reacted to the message."

    user: Optional[MessageUser] = None
    "The user with which the reaction is associated."
