"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Dict, List

from ..custom_base_model import CustomBaseModel


class TabResponseCard(CustomBaseModel):
    """Envelope for cards for a Tab request."""

    card: Dict[str, Any]
    """The adaptive card for this card tab response."""


class TabResponseCards(CustomBaseModel):
    """Envelope for cards for a TabResponse."""

    cards: List["TabResponseCard"]
    """Adaptive cards for this card tab response."""
