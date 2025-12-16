"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from ..custom_base_model import CustomBaseModel
from .tab_context import TabContext
from .tab_entity_context import TabEntityContext


class TabSubmitData(CustomBaseModel):
    """Invoke ('tab/submit') request value payload data."""

    type: Optional[str] = None
    """Should currently be `tab/submit`."""


class TabSubmit(CustomBaseModel):
    """Invoke ('tab/submit') request value payload."""

    tab_context: Optional[TabEntityContext] = None
    """The current tab entity request context."""

    context: Optional[TabContext] = None
    """The current user context, i.e., the current theme."""

    data: Optional[TabSubmitData] = None
    """The data for this tab submit request."""
