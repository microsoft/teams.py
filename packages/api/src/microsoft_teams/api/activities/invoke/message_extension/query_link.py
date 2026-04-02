"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal

from ....models import AppBasedLinkQuery
from ...invoke_activity import InvokeActivity


class MessageExtensionQueryLinkInvokeActivity(InvokeActivity):
    """
    Message extension query link invoke activity for composeExtension/queryLink invokes.

    Represents an invoke activity when a user queries a link
    in a messaging extension.
    """

    name: Literal["composeExtension/queryLink"] = "composeExtension/queryLink"  #
    """The name of the operation associated with an invoke or event activity."""

    value: AppBasedLinkQuery
    """A value that is associated with the activity."""
