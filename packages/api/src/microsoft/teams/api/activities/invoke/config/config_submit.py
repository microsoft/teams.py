"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Literal, Optional

from ....models import ConversationReference
from ...invoke_activity import InvokeActivity
from ...utils import input_model


class ConfigSubmitInvokeActivity(InvokeActivity):
    """
    Represents the config submit invoke activity.
    """

    type: Literal["invoke"] = "invoke"  # pyright: ignore [reportIncompatibleVariableOverride]

    name: Literal["config/submit"] = "config/submit"  # pyright: ignore [reportIncompatibleVariableOverride]
    """The name of the operation associated with an invoke or event activity."""

    value: Any
    """The value associated with the activity."""

    relates_to: Optional[ConversationReference] = None
    """A reference to another conversation or activity."""


@input_model
class ConfigSubmitInvokeActivityInput(ConfigSubmitInvokeActivity):
    """
    Input type for ConfigSubmitInvokeActivity where ActivityBase fields are optional
    but invoke-specific fields retain their required status.
    """

    pass
