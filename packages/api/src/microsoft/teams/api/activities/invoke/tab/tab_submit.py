"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal, Optional

from ....models import ConversationReference, TabRequest
from ...invoke_activity import InvokeActivity
from ...utils import input_model


class TabSubmitInvokeActivity(InvokeActivity):
    """
    Tab submit invoke activity for tab/submit invokes.

    Represents an invoke activity when a tab submits data
    or handles user interaction.
    """

    name: Literal["tab/submit"] = "tab/submit"  # pyright: ignore [reportIncompatibleVariableOverride]
    """The name of the operation associated with an invoke or event activity."""

    value: TabRequest
    """A value that is associated with the activity."""

    relates_to: Optional[ConversationReference] = None
    """A reference to another conversation or activity."""


@input_model
class TabSubmitInvokeActivityInput(TabSubmitInvokeActivity):
    """
    Input type for TabSubmitInvokeActivity where ActivityBase fields are optional
    but invoke-specific fields retain their required status.
    """

    pass
