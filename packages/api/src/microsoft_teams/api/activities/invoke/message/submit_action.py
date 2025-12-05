"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal, Optional

from ....models import ConversationReference, CustomBaseModel
from ...invoke_activity import InvokeActivity


class MessageSubmitActionValue(CustomBaseModel):
    reaction: Literal["like", "dislike"]
    """The reaction triggered"""

    feedback: str
    """The response the user provides when prompted."""


class MessageSubmitActionInvokeValue(CustomBaseModel):
    """
    Represents the value associated with a message submit action.
    """

    action_name: Literal["feedback"] = "feedback"
    """Action name"""

    action_value: MessageSubmitActionValue
    """The value associated with the action."""


class MessageSubmitActionInvokeActivity(InvokeActivity):
    """
    Represents an activity that is sent when a message submit action is invoked.
    """

    name: Literal["message/submitAction"] = "message/submitAction"  #
    """The name of the operation associated with an invoke or event activity."""

    value: MessageSubmitActionInvokeValue
    """The value associated with the activity."""

    relates_to: Optional[ConversationReference] = None
    """A reference to another conversation or activity."""
