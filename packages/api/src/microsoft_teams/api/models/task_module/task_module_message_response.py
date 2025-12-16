"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal

from .task_module_response_base import TaskModuleResponseBase


class TaskModuleMessageResponse(TaskModuleResponseBase):
    """Task Module response with message action."""

    type: Literal["message"] = "message"  #
    """Type of response, always 'message' for this class."""

    value: str
    """Teams will display the value of value in a popup message box."""
