"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from ..custom_base_model import CustomBaseModel


class TabContext(CustomBaseModel):
    """Current tab request context, i.e., the current theme."""

    theme: Optional[str] = None
    """The current user's theme."""
