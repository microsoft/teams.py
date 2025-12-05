"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from ..custom_base_model import CustomBaseModel
from .tab_context import TabContext
from .tab_entity_context import TabEntityContext


class TabRequest(CustomBaseModel):
    """Invoke ('tab/fetch') request value payload."""

    tab_context: Optional[TabEntityContext] = None
    """The current tab entity request context."""

    context: Optional[TabContext] = None
    """The current user context, i.e., the current theme."""

    state: Optional[str] = None
    """The magic code for OAuth flow."""
