"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Dict, List, Optional, Protocol, Union

from ..models.entity.mention_entity import MentionEntity


class TextActivityProtocol(Protocol):
    text: Optional[str]
    entities: Optional[Union[List[MentionEntity], Dict[str, Any]]]
