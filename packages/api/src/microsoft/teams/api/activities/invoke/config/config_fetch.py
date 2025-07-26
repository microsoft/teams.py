"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Literal, Optional

from ....models import ConversationReference, CustomBaseModel
from ...invoke_activity import InvokeActivity


class ConfigFetchInvokeActivity(InvokeActivity, CustomBaseModel):
    """
    Represents the config fetch invoke activity.
    """

    type: Literal["invoke"] = "invoke"  #

    name: Literal["config/fetch"] = "config/fetch"  #
    """The name of the operation associated with an invoke or event activity."""

    value: Any
    """The value associated with the activity."""

    relates_to: Optional[ConversationReference] = None
    """A reference to another conversation or activity."""
