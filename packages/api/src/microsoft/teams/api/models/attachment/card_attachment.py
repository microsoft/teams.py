from typing import Any, Literal, Union

from pydantic import BaseModel, Field

from ..card import AnimationCard, AudioCard, HeroCard, ThumbnailCard, VideoCard


# Placeholder classes
class IAdaptiveCard(BaseModel):
    """Placeholder for @microsoft/teams.cards IAdaptiveCard"""

    pass


class OAuthCard(BaseModel):
    """Placeholder for OAuthCard"""

    pass


class SigninCard(BaseModel):
    """Placeholder for SigninCard"""

    pass


class CardAttachmentData(BaseModel):
    """Base model for a card attachment"""

    content_type: str = Field(..., alias="contentType")
    content: Any


class AdaptiveCardAttachment(CardAttachmentData):
    content_type: Literal["application/vnd.microsoft.card.adaptive"]
    content: IAdaptiveCard


class AnimationCardAttachment(CardAttachmentData):
    content_type: Literal["application/vnd.microsoft.card.animation"]
    content: AnimationCard


class AudioCardAttachment(CardAttachmentData):
    content_type: Literal["application/vnd.microsoft.card.audio"]
    content: AudioCard


class HeroCardAttachment(CardAttachmentData):
    content_type: Literal["application/vnd.microsoft.card.hero"]
    content: HeroCard


class OAuthCardAttachment(CardAttachmentData):
    content_type: Literal["application/vnd.microsoft.card.oauth"]
    content: OAuthCard


class SigninCardAttachment(CardAttachmentData):
    content_type: Literal["application/vnd.microsoft.card.signin"]
    content: SigninCard


class ThumbnailCardAttachment(CardAttachmentData):
    content_type: Literal["application/vnd.microsoft.card.thumbnail"]
    content: ThumbnailCard


class VideoCardAttachment(CardAttachmentData):
    content_type: Literal["application/vnd.microsoft.card.video"]
    content: VideoCard


CardAttachmentTypes = {
    "adaptive": AdaptiveCardAttachment,
    "animation": AnimationCardAttachment,
    "audio": AudioCardAttachment,
    "hero": HeroCardAttachment,
    "oauth": OAuthCardAttachment,
    "signin": SigninCardAttachment,
    "thumbnail": ThumbnailCardAttachment,
    "video": VideoCardAttachment,
}

CardAttachmentType = Literal["adaptive", "animation", "audio", "hero", "oauth", "signin", "thumbnail", "video"]

CardAttachment = Union[
    AdaptiveCardAttachment,
    AnimationCardAttachment,
    AudioCardAttachment,
    HeroCardAttachment,
    OAuthCardAttachment,
    SigninCardAttachment,
    ThumbnailCardAttachment,
    VideoCardAttachment,
]


def card_attachment(type: CardAttachmentType, content: Any) -> CardAttachment:
    """
    Create a card attachment of the specified type

    Args:
        type: The type of card attachment to create
        content: The content for the card attachment (specific type based on card type)

    Returns:
        A card attachment of the specified type with the given content
    """
    attachment_class = CardAttachmentTypes[type]
    attachment: CardAttachment = attachment_class(
        content_type=f"application/vnd.microsoft.card.{type}", content=content
    )
    return attachment
