"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from ..custom_base_model import CustomBaseModel


class EntityBase(CustomBaseModel):
    """Base entity for entity types."""

    type: str
    "Type identifier for the entity."
