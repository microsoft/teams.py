"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal, Optional

from ....models import ConversationReference, MessagingExtensionAction
from ...invoke_activity import InvokeActivity


class MessageExtensionSubmitActionInvokeActivity(InvokeActivity):
    """
    Message extension submit action invoke activity for composeExtension/submitAction invokes.

    Represents an invoke activity when a user submits an action
    in a messaging extension.
    """

    name: Literal["composeExtension/submitAction"] = "composeExtension/submitAction"  #
    """The name of the operation associated with an invoke or event activity."""

    value: MessagingExtensionAction
    """A value that is associated with the activity."""

    relates_to: Optional[ConversationReference] = None
    """A reference to another conversation or activity."""
