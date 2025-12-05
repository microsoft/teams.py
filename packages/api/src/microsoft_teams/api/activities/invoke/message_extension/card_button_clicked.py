"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Literal, Optional

from ....models import ConversationReference
from ...invoke_activity import InvokeActivity


class MessageExtensionCardButtonClickedInvokeActivity(InvokeActivity):
    """
    Message extension card button clicked invoke activity for composeExtension/onCardButtonClicked invokes.

    Represents an invoke activity when a user clicks a button
    on a card within a messaging extension.
    """

    name: Literal["composeExtension/onCardButtonClicked"] = "composeExtension/onCardButtonClicked"  #
    """The name of the operation associated with an invoke or event activity."""

    value: Any
    """A value that is associated with the activity."""

    relates_to: Optional[ConversationReference] = None
    """A reference to another conversation or activity."""
