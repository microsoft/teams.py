"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal, Optional

from ....models import ConversationReference, TaskModuleRequest
from ...invoke_activity import InvokeActivity


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
