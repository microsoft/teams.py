"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from pydantic import Field

from ..custom_base_model import CustomBaseModel


class ThreadInfo(CustomBaseModel):
    """Thread metadata supplied by Teams on inbound activities."""

    id: Optional[str] = Field(default=None, frozen=True)
    """ID of the root message that identifies the current thread."""
