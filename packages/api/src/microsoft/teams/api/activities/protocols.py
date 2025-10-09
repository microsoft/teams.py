"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import List, Optional, Protocol, runtime_checkable

from ..models import Entity


@runtime_checkable
class TextActivityProtocol(Protocol):
    """
    Protocol representing a text-based activity.

    Attributes:
        text (str): The textual content of the activity.
        entities (Optional[List[Entity]]): A list of entities associated with the text, such as mentions or links.
    """

    text: str
    entities: Optional[List[Entity]]
