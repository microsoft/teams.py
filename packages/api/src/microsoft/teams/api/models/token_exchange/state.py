"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from ..conversation import ConversationReference
from ..custom_base_model import CustomBaseModel


class TokenExchangeState(CustomBaseModel):
    """
    State object passed to the bot token service.
    """

    connection_name: str
    """The name of the connection used for token exchange."""

    conversation: ConversationReference
    "A reference to the conversation"

    relates_to: Optional[ConversationReference] = None
    "A reference to a related parent conversation."

    ms_app_id: str
    "The URL of the bot messaging endpoint."
