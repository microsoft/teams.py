"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from ..custom_base_model import CustomBaseModel
from .message_app import MessageApp
from .message_conversation import MessageConversation
from .message_user import MessageUser


class MessageFrom(CustomBaseModel):
    """
    Represents a user, application, or conversation type that either sent or was
    referenced in a message.
    """

    user: Optional[MessageUser] = None
    "Represents details of the user."

    application: Optional[MessageApp] = None
    "Represents details of the app."

    conversation: Optional[MessageConversation] = None
    "Represents details of the conversation."
