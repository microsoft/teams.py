"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal

from ....models import CustomBaseModel
from ...invoke_activity import InvokeActivity


class MessageFetchTaskActionValue(CustomBaseModel):
    """The nested action value containing the user's reaction."""

    reaction: Literal["like", "dislike"]
    """The feedback button the user clicked."""


class MessageFetchTaskData(CustomBaseModel):
    """The data payload nested inside the fetch task value."""

    action_name: Literal["feedback"] = "feedback"
    """The name of the action."""

    action_value: MessageFetchTaskActionValue
    """Contains the user's reaction."""


class MessageFetchTaskInvokeValue(CustomBaseModel):
    """
    Represents the value associated with a message fetch task.
    """

    data: MessageFetchTaskData
    """The data payload containing action name and value."""


class MessageFetchTaskInvokeActivity(InvokeActivity):
    """
    Represents an activity sent when a message has a custom feedback loop
    and the user clicks a feedback button.
    The bot should respond with a task module (dialog) to collect feedback.
    """

    name: Literal["message/fetchTask"] = "message/fetchTask"
    """The name of the operation associated with an invoke or event activity."""

    value: MessageFetchTaskInvokeValue
    """The value associated with the activity."""
