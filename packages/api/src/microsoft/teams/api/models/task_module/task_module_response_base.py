"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal, Optional

from ..custom_base_model import CustomBaseModel


class TaskModuleResponseBase(CustomBaseModel):
    """Base class for Task Module responses."""

    type: Optional[Literal["message", "continue"]] = None
    """Choice of action options when responding to the task/submit message."""
