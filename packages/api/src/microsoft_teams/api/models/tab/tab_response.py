"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal, Optional

from ..custom_base_model import CustomBaseModel
from .tab_response_card import TabResponseCards
from .tab_suggested_actions import TabSuggestedActions


class TabResponsePayload(CustomBaseModel):
    """Payload for Tab Response."""

    type: Optional[Literal["continue", "auth", "silentAuth"]] = None
    """Choice of action options when responding to the tab/fetch message."""

    value: Optional[TabResponseCards] = None
    """The TabResponseCards to send when responding to tab/fetch activity with type of 'continue'."""

    suggested_actions: Optional[TabSuggestedActions] = None
    """The Suggested Actions for this card tab."""


class TabResponse(CustomBaseModel):
    """Envelope for Card Tab Response Payload."""

    tab: TabResponsePayload
    """The response to the tab/fetch message."""
