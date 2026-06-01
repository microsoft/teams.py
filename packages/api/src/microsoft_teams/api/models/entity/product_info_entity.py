"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal

from .entity_base import EntityBase


class ProductInfoEntity(EntityBase):
    """Product information entity"""

    id: str
    "Product identifier (ex COPILOT)"

    type: Literal["ProductInfo"] = "ProductInfo"
    "Type identifier for product info"
