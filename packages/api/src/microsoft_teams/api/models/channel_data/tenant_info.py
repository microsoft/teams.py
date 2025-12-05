"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from ..custom_base_model import CustomBaseModel


class TenantInfo(CustomBaseModel):
    """
    Describes a tenant
    """

    id: str
    "Unique identifier representing a tenant"
