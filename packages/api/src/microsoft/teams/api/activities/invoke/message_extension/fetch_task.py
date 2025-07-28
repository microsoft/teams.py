"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal, Optional

from ....models import ConversationReference, MessagingExtensionAction
from ...invoke_activity import InvokeActivity


class MessageExtensionFetchTaskInvokeActivity(InvokeActivity):
    """
    Message extension fetch task invoke activity for composeExtension/fetchTask invokes.

    Represents an invoke activity when a messaging extension needs to
    fetch a task module for user interaction.
    """

    name: Literal["composeExtension/fetchTask"] = "composeExtension/fetchTask"  #
    """The name of the operation associated with an invoke or event activity."""

    value: MessagingExtensionAction
    """A value that is associated with the activity."""

    relates_to: Optional[ConversationReference] = None
    """A reference to another conversation or activity."""
