"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal

from ....models import MessagingExtensionQuery
from ...invoke_activity import InvokeActivity


class MessageExtensionSettingInvokeActivity(InvokeActivity):
    """
    Message extension setting invoke activity for composeExtension/setting invokes.

    Represents an invoke activity when a messaging extension processes
    setting-related operations.
    """

    name: Literal["composeExtension/setting"] = "composeExtension/setting"  #
    """The name of the operation associated with an invoke or event activity."""

    value: MessagingExtensionQuery
    """A value that is associated with the activity."""
