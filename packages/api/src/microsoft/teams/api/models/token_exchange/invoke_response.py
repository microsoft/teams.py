"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from ..custom_base_model import CustomBaseModel


class TokenExchangeInvokeResponse(CustomBaseModel):
    """
    The response object of a token exchange invoke
    """

    id: str
    """The id from the OauthCard"""

    connection_name: str
    """The connection name"""

    failure_detail: str
    """The details of why the token exchange failed"""
