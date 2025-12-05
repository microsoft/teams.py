"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal, Optional

from ...models import ConversationReference, CustomBaseModel
from ..invoke_activity import InvokeActivity


class HandoffActionValue(CustomBaseModel):
    """Value object for handoff action invoke activities."""

    continuation: str
    """Continuation token used to get the conversation reference."""


class HandoffActionInvokeActivity(InvokeActivity):
    """
    Handoff action invoke activity for handoff/action invokes.

    Represents an invoke activity when a handoff action occurs,
    typically used for transferring conversation control.
    """

    name: Literal["handoff/action"] = "handoff/action"  #
    """The name of the operation associated with an invoke or event activity."""

    value: HandoffActionValue
    """A value that is associated with the activity."""

    relates_to: Optional[ConversationReference] = None
    """A reference to another conversation or activity."""
