"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal, Optional

from ....models import AppBasedLinkQuery, ConversationReference
from ...invoke_activity import InvokeActivity


class MessageExtensionAnonQueryLinkInvokeActivity(InvokeActivity):
    """
    Message extension anonymous query link invoke activity for composeExtension/anonymousQueryLink invokes.

    Represents an invoke activity when an anonymous user queries a link
    in a messaging extension.
    """

    name: Literal["composeExtension/anonymousQueryLink"] = "composeExtension/anonymousQueryLink"  #
    """The name of the operation associated with an invoke or event activity."""

    value: AppBasedLinkQuery
    """A value that is associated with the activity."""

    relates_to: Optional[ConversationReference] = None
    """A reference to another conversation or activity."""
