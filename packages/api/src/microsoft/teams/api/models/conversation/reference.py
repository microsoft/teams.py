"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from pydantic import AliasGenerator, BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from ..account import Account
from ..channel_id import ChannelID
from ..conversation_account import ConversationAccount


class ConversationReference(BaseModel):
    """An object relating to a particular point in a conversation."""

    model_config = ConfigDict(
        alias_generator=AliasGenerator(
            serialization_alias=to_camel,
        ),
        extra="allow",
    )

    activity_id: Optional[str] = Field(
        default=None,
        description="ID of the activity to refer to",
    )

    user: Optional[Account] = Field(
        default=None,
        description="User participating in this conversation",
    )

    locale: Optional[str] = Field(
        default=None,
        description=(
            "A locale name for the contents of the text field. "
            "The locale name is a combination of an ISO 639 two- or three-letter "
            "culture code associated with a language and an ISO 3166 two-letter "
            "subculture code associated with a country or region. "
            "The locale name can also correspond to a valid BCP-47 language tag."
        ),
    )

    bot: Account = Field(
        description="Bot participating in this conversation",
    )

    conversation: ConversationAccount = Field(
        description="Conversation reference",
    )

    channel_id: ChannelID = Field(
        description="Channel ID",
    )

    service_url: str = Field(
        description="Service endpoint where operations concerning the referenced conversation may be performed",
    )
