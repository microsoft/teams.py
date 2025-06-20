"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import List, Optional

from microsoft.teams.api.models.card.card_action import CardAction

from ..custom_base_model import CustomBaseModel


class SignInCard(CustomBaseModel):
    """
    A card representing a request to sign in
    """

    title: Optional[str] = None
    """
    Title of this card
    """

    subtitle: Optional[str] = None
    """
    Subtitle of this card
    """

    text: Optional[str] = None
    """
    Text for signin request.
    """

    buttons: List[CardAction]
    """
    Action to use to perform signin
    """
