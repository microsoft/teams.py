"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from ..account import Account, ConversationAccount
from ..channel_id import ChannelID
from ..custom_base_model import CustomBaseModel


class ConversationReference(CustomBaseModel):
    """
    An object relating to a particular point in a conversation
    """

    activity_id: Optional[str] = None
    "(Optional) ID of the activity to refer to"

    user: Optional[Account] = None
    "(Optional) User participating in this conversation"

    locale: Optional[str] = None
    """
     Combination of an ISO 639 two- or three-letter culture code associated with a language
    nd an ISO 3166 two-letter subculture code associated with a country or region. The locale name
    an also correspond to a valid BCP-47 language tag.
    """

    bot: Account
    "Bot participating in this conversation"

    conversation: ConversationAccount
    "Conversation reference"

    channel_id: ChannelID
    "Channel ID"

    service_url: str
    "Service endpoint where operations concerning the referenced conversation may be performed"
