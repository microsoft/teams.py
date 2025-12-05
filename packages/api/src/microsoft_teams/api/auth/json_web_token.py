"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import time
from typing import Optional, Union

import jwt
from pydantic import BaseModel, ConfigDict

from .caller import CallerIds, CallerType
from .token import TokenProtocol


class JsonWebTokenPayload(BaseModel):
    """JWT payload with additional Teams-specific fields."""

    model_config = ConfigDict(extra="allow")

    aud: Optional[Union[str, list[str]]] = None
    iss: Optional[str] = None
    exp: Optional[int] = None
    kid: Optional[str] = None
    appid: Optional[str] = None
    app_displayname: Optional[str] = None
    tid: Optional[str] = None
    version: Optional[str] = None
    serviceurl: Optional[str] = None


class JsonWebToken(TokenProtocol):
    """JSON Web Token implementation for Teams authentication."""

    def __init__(self, value: str):
        """
        Initialize JWT from token string.

        Args:
            value: The JWT token string.
        """
        self._value = value
        # Decode without verification for payload extraction
        self._payload = JsonWebTokenPayload(
            **jwt.decode(value, algorithms=["RS256"], options={"verify_signature": False})
        )

    @property
    def audience(self) -> Optional[Union[str, list[str]]]:
        """The token audience."""
        return self._payload.aud

    @property
    def issuer(self) -> Optional[str]:
        """The token issuer."""
        return self._payload.iss

    @property
    def key_id(self) -> Optional[str]:
        """The key ID."""
        return self._payload.kid

    @property
    def app_id(self) -> str:
        """The app ID."""
        return self._payload.appid or ""

    @property
    def app_display_name(self) -> Optional[str]:
        """The app display name."""
        return self._payload.app_displayname

    @property
    def tenant_id(self) -> Optional[str]:
        """The tenant ID."""
        return self._payload.tid

    @property
    def version(self) -> Optional[str]:
        """The token version."""
        return self._payload.version

    @property
    def service_url(self) -> str:
        """The service URL to send responses to."""
        url = self._payload.serviceurl or "https://smba.trafficmanager.net/teams"

        if url.endswith("/"):
            url = url[:-1]

        return url

    @property
    def from_(self) -> CallerType:
        """Where the activity originated from."""
        if self.app_id:
            return "bot"
        return "azure"

    @property
    def from_id(self) -> str:
        """The id of the activity sender."""
        if self.from_ == "bot":
            return f"{CallerIds.BOT}:{self.app_id}"
        return CallerIds.AZURE

    @property
    def expiration(self) -> Optional[int]:
        """The expiration of the token since epoch in milliseconds."""
        if self._payload.exp:
            return self._payload.exp * 1000
        return None

    def is_expired(self, buffer_ms: int = 5 * 60 * 1000) -> bool:
        """
        Check if the token is expired.

        Args:
            buffer_ms: Buffer time in milliseconds (default 5 minutes).

        Returns:
            True if the token is expired, False otherwise.
        """
        if not self.expiration:
            return False
        return self.expiration < (time.time() * 1000) + buffer_ms

    def __str__(self) -> str:
        """String form of the token."""
        return self._value
