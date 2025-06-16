from typing import Optional

from pydantic import BaseModel, Field


# Placeholder for external types
class Account(BaseModel):
    """Placeholder for Account model from ../account"""

    pass


class ConversationAccount(BaseModel):
    """Placeholder for ConversationAccount model from ../account"""

    pass


class ChannelID(str):
    """Placeholder for ChannelID type from ../channel-id"""

    pass


class ConversationReference(BaseModel):
    """
    An object relating to a particular point in a conversation
    """

    activity_id: Optional[str] = Field(
        None, description="(Optional) ID of the activity to refer to", alias="activityId"
    )
    user: Optional[Account] = Field(None, description="(Optional) User participating in this conversation")
    locale: Optional[str] = Field(
        None,
        description="Combination of an ISO 639 two- or three-letter culture code associated with a language"
        + " and an ISO 3166 two-letter subculture code associated with a country or region. The locale name"
        + " can also correspond to a valid BCP-47 language tag.",
    )
    bot: Account = Field(..., description="Bot participating in this conversation")
    conversation: ConversationAccount = Field(..., description="Conversation reference")
    channel_id: ChannelID = Field(..., description="Channel ID", alias="channelId")
    service_url: str = Field(
        ...,
        description="Service endpoint where operations concerning the referenced conversation may be performed",
        alias="serviceUrl",
    )
