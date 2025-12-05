"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from ..custom_base_model import CustomBaseModel


class TokenExchangeInvokeRequest(CustomBaseModel):
    """
    A request to exchange a token.
    """

    id: str
    "The id from the OauthCard"

    connection_name: str
    "The connection name"

    token: str
    "The user token that can be exchanged."
