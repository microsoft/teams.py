"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from .custom_base_model import CustomBaseModel


class AppBasedLinkQuery(CustomBaseModel):
    """
    An interface representing AppBasedLinkQuery.
    Invoke request body type for app-based link query.
    """

    url: Optional[str] = None
    "Url queried by user"

    state: Optional[str] = None
    "State is the magic code for Oauth flow"
