"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from .task_module_response_base import TaskModuleResponseBase


class TaskModuleCardResponse(TaskModuleResponseBase):
    """Tab response to 'task/submit'."""

    value: Optional[str] = None
    """JSON for Adaptive cards to appear in the tab."""
