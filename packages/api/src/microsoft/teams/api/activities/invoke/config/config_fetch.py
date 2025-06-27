"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Literal, Optional

from ....models import ConversationReference, CustomBaseModel
from ...activity import Activity


class ConfigFetchInvokeActivity(Activity, CustomBaseModel):
    """
    Represents the config fetch invoke activity.
    """

    _type: Literal["invoke"] = "invoke"

    name: Literal["config/fetch"] = "config/fetch"
    """The name of the operation associated with an invoke or event activity."""

    value: Any
    """The value associated with the activity."""

    relates_to: Optional[ConversationReference] = None
    """A reference to another conversation or activity."""
