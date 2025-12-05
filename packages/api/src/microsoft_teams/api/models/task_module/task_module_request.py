"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Optional

from ..custom_base_model import CustomBaseModel
from ..tab import TabEntityContext


class TaskModuleRequestContext(CustomBaseModel):
    """Current user context, i.e., the current theme."""

    theme: Optional[str] = None
    """The current theme."""


class TaskModuleRequest(CustomBaseModel):
    """Task module invoke request value payload."""

    data: Optional[Any] = None
    """User input data. Free payload with key-value pairs."""

    context: Optional[TaskModuleRequestContext] = None
    """Current user context, i.e., the current theme."""

    tab_context: Optional[TabEntityContext] = None
    """Tab request context."""
