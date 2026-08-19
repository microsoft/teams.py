"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from ..custom_base_model import CustomBaseModel


class TenantInfo(CustomBaseModel):
    """
    Describes a tenant
    """

    id: Optional[str] = None
    "Unique identifier representing a tenant"
