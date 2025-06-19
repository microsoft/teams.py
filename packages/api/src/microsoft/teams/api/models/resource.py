"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from .custom_base_model import CustomBaseModel


class Resource(CustomBaseModel):
    """A response containing a resource ID."""

    id: str
    """Id of the resource."""
