"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from ..custom_base_model import CustomBaseModel


class SignInExchangeToken(CustomBaseModel):
    """SignInExchangeToken"""

    id: str
    """
    The ID of the sign-in exchange token
    """
    token: Optional[str] = None
    """
    The token for the sign-in exchange"
    """
    connection_name: str
    """
    The connection name
    """
