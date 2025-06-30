"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import List, Optional, Protocol, runtime_checkable

from ..models.entity import Entity


@runtime_checkable
class TextActivityProtocol(Protocol):
    text: str
    entities: Optional[List[Entity]]
