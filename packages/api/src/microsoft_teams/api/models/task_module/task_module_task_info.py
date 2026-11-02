"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Annotated, Literal, Optional, Union

from pydantic import Field

from ..attachment import Attachment
from ..custom_base_model import CustomBaseModel

TaskModuleDimension = Union[Literal["small", "medium", "large"], str]


class BaseTaskModuleTaskInfo(CustomBaseModel):
    """Base class for task module task info."""

    title: Optional[str] = None
    """Appears below the app name and to the right of the app icon."""

    height: Optional[Annotated[Union[int, TaskModuleDimension], Field(union_mode="left_to_right")]] = None
    """Can be a number (pixels) or string ('small', 'medium', 'large')."""

    width: Optional[Annotated[Union[int, TaskModuleDimension], Field(union_mode="left_to_right")]] = None
    """Can be a number (pixels) or string ('small', 'medium', 'large')."""

    fallback_url: Optional[str] = None
    """If a client doesn't support task module feature, this URL opens in browser."""

    completion_bot_id: Optional[str] = None
    """If a client doesn't support task module feature, this URL opens in browser."""


class CardTaskModuleTaskInfo(BaseTaskModuleTaskInfo):
    """Task module info for card type."""

    card: Attachment
    """The JSON for the Adaptive card to appear in the task module."""


class UrlTaskModuleTaskInfo(BaseTaskModuleTaskInfo):
    """Task module info for URL type."""

    url: str
    """The URL of what is loaded as an iframe inside the task module."""


TaskModuleTaskInfo = Union[CardTaskModuleTaskInfo, UrlTaskModuleTaskInfo]
