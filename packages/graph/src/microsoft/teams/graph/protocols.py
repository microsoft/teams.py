"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import datetime
from typing import Optional, Protocol, runtime_checkable


@runtime_checkable
class TokenProtocol(Protocol):
    """
    Protocol representing an access token with metadata.

    Attributes:
        access_token (str): The actual access token string.
        expires_at (Optional[datetime.datetime]): When the token expires (UTC timezone).
        token_type (Optional[str]): Type of token, usually "Bearer".
        scope (Optional[str]): Scopes associated with the token.
    """

    access_token: str
    expires_at: Optional[datetime.datetime]
    token_type: Optional[str]
    scope: Optional[str]
