"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Literal, Optional

from ....models import ConversationReference
from ...invoke_activity import InvokeActivity


class MessageExtensionSelectItemInvokeActivity(InvokeActivity):
    """
    Message extension select item invoke activity for composeExtension/selectItem invokes.

    Represents an invoke activity when a user selects an item
    from a messaging extension search result.
    """

    name: Literal["composeExtension/selectItem"] = "composeExtension/selectItem"  #
    """The name of the operation associated with an invoke or event activity."""

    value: Any
    """A value that is associated with the activity."""

    relates_to: Optional[ConversationReference] = None
    """A reference to another conversation or activity."""
