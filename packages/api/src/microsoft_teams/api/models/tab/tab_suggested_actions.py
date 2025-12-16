"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import List

from ..card import CardAction
from ..custom_base_model import CustomBaseModel


class TabSuggestedActions(CustomBaseModel):
    """Tab SuggestedActions (Only when type is 'auth' or 'silentAuth')."""

    actions: List[CardAction]
    """Actions to show in the card response."""
