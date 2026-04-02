"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal

from ....models import TaskModuleRequest
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
