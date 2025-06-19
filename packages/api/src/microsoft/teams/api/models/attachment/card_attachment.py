"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from enum import Enum
from typing import Any, Literal, Union

from microsoft.teams.cards import AdaptiveCard

from ..card import AnimationCard, AudioCard, HeroCard, ThumbnailCard, VideoCard
from ..custom_base_model import CustomBaseModel
from ..oauth import OAuthCard
from ..sign_in import SignInCard


class CardAttachmentData(CustomBaseModel):
    """Base model for a card attachment"""

    content_type: str
    content: Any


class AdaptiveCardAttachment(CardAttachmentData):
    content_type: Literal["application/vnd.microsoft.card.adaptive"]
    content: AdaptiveCard


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
    content: SignInCard


class ThumbnailCardAttachment(CardAttachmentData):
    content_type: Literal["application/vnd.microsoft.card.thumbnail"]
    content: ThumbnailCard


class VideoCardAttachment(CardAttachmentData):
    content_type: Literal["application/vnd.microsoft.card.video"]
    content: VideoCard


class CardAttachmentTypes(str, Enum):
    ADAPTIVE = AdaptiveCardAttachment
    ANIMATION = AnimationCardAttachment
    AUDIO = AudioCardAttachment
    HERO = HeroCardAttachment
    OAUTH = OAuthCardAttachment
    SIGN_IN = SigninCardAttachment
    THUMBNAIL = ThumbnailCardAttachment
    VIDEO = VideoCardAttachment
    UNKNOWN = object

    @classmethod
    def _missing_(cls, value: object) -> "CardAttachmentTypes":
        """Return unknown value for missing enum values."""
        return cls.UNKNOWN


class CardAttachmentType(str, Enum):
    ADAPTIVE = "adaptive"
    ANIMATION = "animation"
    AUDIO = "audio"
    HERO = "hero"
    OAUTH = "oauth"
    SIGN_IN = "signin"
    THUMBNAIL = "thumbnail"
    VIDEO = "video"
    UNKNOWN = "unknown"

    @classmethod
    def _missing_(cls, value: object) -> "CardAttachmentType":
        """Return unknown value for missing enum values."""
        return cls.UNKNOWN


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


def card_attachment(type: CardAttachmentTypes, content: Any) -> CardAttachment:
    """
    Create a card attachment of the specified type

    Args:
        type: The type of card attachment to create
        content: The content for the card attachment (specific type based on card type)

    Returns:
        A card attachment of the specified type with the given content
    """
    attachment_class = type.value
    attachment_type = CardAttachmentType(type.name)
    attachment: CardAttachment = attachment_class(
        content_type=f"application/vnd.microsoft.card.{attachment_type.value}", content=content
    )
    return attachment
