"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Annotated, Any, Union, cast

from pydantic import Discriminator, Tag

from .ai_message_entity import AIMessageEntity
from .citation_entity import CitationEntity
from .client_info_entity import ClientInfoEntity
from .entity_base import EntityBase
from .mention_entity import MentionEntity
from .message_entity import MessageEntity
from .product_info_entity import ProductInfoEntity
from .quoted_reply_entity import QuotedReplyEntity
from .sensitive_usage_entity import SensitiveUsageEntity
from .stream_info_entity import StreamInfoEntity
from .targeted_message_info_entity import TargetedMessageInfoEntity

_KNOWN_ENTITY_TYPE_TAGS = {
    "clientInfo": "clientInfo",
    "mention": "mention",
    "ProductInfo": "ProductInfo",
    "quotedReply": "quotedReply",
    "streaminfo": "streaminfo",
    "targetedMessageInfo": "targetedMessageInfo",
}


def _entity_discriminator(value: Any) -> str:
    if isinstance(value, CitationEntity):
        return "citation"
    if isinstance(value, SensitiveUsageEntity):
        return "sensitiveUsage"
    if isinstance(value, AIMessageEntity):
        return "aiMessage"

    data = cast(dict[str, Any], value) if isinstance(value, dict) else None
    entity_type = data.get("type") if data is not None else getattr(cast(object, value), "type", None)
    if not isinstance(entity_type, str):
        return "_unknown"

    if entity_type == "https://schema.org/Message":
        if data is not None:
            if "citation" in data:
                return "citation"
            if "usageInfo" in data or "usage_info" in data:
                return "sensitiveUsage"

            additional_type = data.get("additionalType", data.get("additional_type"))
            if isinstance(additional_type, list) and "AIGeneratedContent" in additional_type:
                return "aiMessage"

        return "https://schema.org/Message"

    return _KNOWN_ENTITY_TYPE_TAGS.get(entity_type, "_unknown")


Entity = Annotated[
    Union[
        Annotated[ClientInfoEntity, Tag("clientInfo")],
        Annotated[MentionEntity, Tag("mention")],
        Annotated[MessageEntity, Tag("https://schema.org/Message")],
        Annotated[AIMessageEntity, Tag("aiMessage")],
        Annotated[StreamInfoEntity, Tag("streaminfo")],
        Annotated[CitationEntity, Tag("citation")],
        Annotated[SensitiveUsageEntity, Tag("sensitiveUsage")],
        Annotated[ProductInfoEntity, Tag("ProductInfo")],
        Annotated[QuotedReplyEntity, Tag("quotedReply")],
        Annotated[TargetedMessageInfoEntity, Tag("targetedMessageInfo")],
        Annotated[EntityBase, Tag("_unknown")],
    ],
    Discriminator(_entity_discriminator),
]
