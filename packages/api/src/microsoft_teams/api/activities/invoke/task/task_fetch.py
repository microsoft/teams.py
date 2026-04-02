"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal

from ....models import TaskModuleRequest
from ...invoke_activity import InvokeActivity


class TaskFetchInvokeActivity(InvokeActivity):
    """
    Task fetch invoke activity for task/fetch invokes.

    Represents an invoke activity when a task module needs to fetch
    configuration or content for display.
    """

    name: Literal["task/fetch"] = "task/fetch"  #
    """The name of the operation associated with an invoke or event activity."""

    value: TaskModuleRequest
    """A value that is associated with the activity."""
