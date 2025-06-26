"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Union

from .ai_message_entity import AIMessageEntity
from .citation_entity import CitationEntity
from .client_info_entity import ClientInfoEntity
from .mention_entity import MentionEntity
from .message_entity import MessageEntity
from .sensitive_usage_entity import SensitiveUsageEntity
from .stream_info_entity import StreamInfoEntity

Entity = Union[
    ClientInfoEntity,
    MentionEntity,
    MessageEntity,
    AIMessageEntity,
    StreamInfoEntity,
    CitationEntity,
    SensitiveUsageEntity,
]
