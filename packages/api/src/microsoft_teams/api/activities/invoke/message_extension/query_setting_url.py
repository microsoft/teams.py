"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal, Optional

from ....models import ConversationReference, MessagingExtensionQuery
from ...invoke_activity import InvokeActivity


class MessageExtensionQuerySettingUrlInvokeActivity(InvokeActivity):
    """
    Message extension query setting URL invoke activity for composeExtension/querySettingUrl invokes.

    Represents an invoke activity when a messaging extension needs to
    query for setting URL configuration.
    """

    name: Literal["composeExtension/querySettingUrl"] = "composeExtension/querySettingUrl"  #
    """The name of the operation associated with an invoke or event activity."""

    value: MessagingExtensionQuery
    """A value that is associated with the activity."""

    relates_to: Optional[ConversationReference] = None
    """A reference to another conversation or activity."""
