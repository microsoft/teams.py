"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal

from ..custom_base_model import CustomBaseModel


class ProductInfoEntity(CustomBaseModel):
    """Product information entity"""

    id: str
    "Product identifier (ex COPILOT)"

    type: Literal["ProductInfo"] = "ProductInfo"
    "Type identifier for product info"
