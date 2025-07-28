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
from .attachment import Attachment


class CardAttachmentData(CustomBaseModel):
    """Base model for a card attachment"""

    content_type: str
    content: Any


class AdaptiveCardAttachment(CardAttachmentData):
    content_type: Literal["application/vnd.microsoft.card.adaptive"] = "application/vnd.microsoft.card.adaptive"  #
    content: AdaptiveCard


class AnimationCardAttachment(CardAttachmentData):
    content_type: Literal["application/vnd.microsoft.card.animation"] = "application/vnd.microsoft.card.animation"  #
    content: AnimationCard


class AudioCardAttachment(CardAttachmentData):
    content_type: Literal["application/vnd.microsoft.card.audio"] = "application/vnd.microsoft.card.audio"  #
    content: AudioCard


class HeroCardAttachment(CardAttachmentData):
    content_type: Literal["application/vnd.microsoft.card.hero"] = "application/vnd.microsoft.card.hero"  #
    content: HeroCard


class OAuthCardAttachment(CardAttachmentData):
    content_type: Literal["application/vnd.microsoft.card.oauth"] = "application/vnd.microsoft.card.oauth"  #
    content: OAuthCard


class SigninCardAttachment(CardAttachmentData):
    content_type: Literal["application/vnd.microsoft.card.signin"] = "application/vnd.microsoft.card.signin"  #
    content: SignInCard


class ThumbnailCardAttachment(CardAttachmentData):
    content_type: Literal["application/vnd.microsoft.card.thumbnail"] = "application/vnd.microsoft.card.thumbnail"  #
    content: ThumbnailCard


class VideoCardAttachment(CardAttachmentData):
    content_type: Literal["application/vnd.microsoft.card.video"] = "application/vnd.microsoft.card.video"  #
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


class CardAttachmentType(str, Enum):
    ADAPTIVE = "adaptive"
    ANIMATION = "animation"
    AUDIO = "audio"
    HERO = "hero"
    OAUTH = "oauth"
    SIGN_IN = "signin"
    THUMBNAIL = "thumbnail"
    VIDEO = "video"


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


def card_attachment(attachment: CardAttachment) -> Attachment:
    """
    Create a card attachment of the specified type

    Args:
        type: The type of card attachment to create
        content: The content for the card attachment (specific type based on card type)

    Returns:
        A card attachment of the specified type with the given content
    """
    return Attachment(
        content_type=attachment.content_type,
        content=attachment.content,
    )
