"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from ..custom_base_model import CustomBaseModel


class AppInfo(CustomBaseModel):
    """
    Describes an app
    """

    id: str
    "Unique identifier representing an app"
