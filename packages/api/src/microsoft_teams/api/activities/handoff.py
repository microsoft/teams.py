"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal

from ..models import ActivityBase, ActivityInputBase, CustomBaseModel


class _HandoffBase(CustomBaseModel):
    """Base class containing shared handoff activity fields (all Optional except type)."""

    type: Literal["handoff"] = "handoff"


class HandoffActivity(_HandoffBase, ActivityBase):
    """Output model for received handoff activities with required fields and read-only properties."""


class HandoffActivityInput(_HandoffBase, ActivityInputBase):
    """Input model for creating handoff activities with builder methods."""
