"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal, Optional

from ....models import ConversationReference, TaskModuleRequest
from ...invoke_activity import InvokeActivity
from ...utils import input_model


class TaskSubmitInvokeActivity(InvokeActivity):
    """
    Task submit invoke activity for task/submit invokes.

    Represents an invoke activity when a task module handles
    user submission or interaction.
    """

    name: Literal["task/submit"] = "task/submit"  #
    """The name of the operation associated with an invoke or event activity."""

    value: TaskModuleRequest
    """A value that is associated with the activity."""

    relates_to: Optional[ConversationReference] = None
    """A reference to another conversation or activity."""


@input_model
class TaskSubmitInvokeActivityInput(TaskSubmitInvokeActivity):
    """
    Input type for TaskSubmitInvokeActivity where ActivityBase fields are optional
    but invoke-specific fields retain their required status.
    """

    pass
