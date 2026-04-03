"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal

from ....models import MessagingExtensionQuery
from ...invoke_activity import InvokeActivity


class MessageExtensionQueryInvokeActivity(InvokeActivity):
    """
    Message extension query invoke activity for composeExtension/query invokes.

    Represents an invoke activity when a user performs a search query
    in a messaging extension.
    """

    name: Literal["composeExtension/query"] = "composeExtension/query"  #
    """The name of the operation associated with an invoke or event activity."""

    value: MessagingExtensionQuery
    """A value that is associated with the activity."""
