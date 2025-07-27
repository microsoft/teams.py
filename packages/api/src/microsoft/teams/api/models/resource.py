"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from .custom_base_model import CustomBaseModel


class Resource(CustomBaseModel):
    """A response containing a resource ID."""

    id: Optional[str] = None
    """Id of the resource."""
