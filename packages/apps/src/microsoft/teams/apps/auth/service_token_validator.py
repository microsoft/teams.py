"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Dict, Optional

import jwt
from jwt import PyJWKClient
from microsoft.teams.api import JsonWebToken
from microsoft.teams.common.logging import ConsoleLogger


class ServiceTokenValidator:
    """
    Bot Framework JWT token validator using PyJWKClient for simplified validation.

    Reference: https://learn.microsoft.com/en-us/azure/bot-service/rest-api/bot-framework-rest-connector-authentication
    """

    def __init__(self, app_id: str, logger: Optional[Any] = None):
        """
        Initialize the Bot Framework token validator.

        Args:
            app_id: The bot's Microsoft App ID (used for audience validation)
            logger: Optional logger instance
        """
        self.app_id = app_id
        self.logger = logger or ConsoleLogger().create_logger("@teams/bot-token-validator")

        # Bot Framework JWKS endpoint - PyJWKClient handles caching automatically
        self.jwks_client = PyJWKClient("https://login.botframework.com/v1/.well-known/keys")

    async def validate_token(self, raw_token: str, service_url: Optional[str] = None) -> JsonWebToken:
        """
        Validate a Bot Framework JWT token.

        Args:
            raw_token: The raw JWT token string
            service_url: Optional service URL to validate against token claims

        Returns:
            JsonWebToken if valid

        Raises:
            jwt.InvalidTokenError: When token validation fails
        """
        if not raw_token:
            self.logger.error("No token provided")
            raise jwt.InvalidTokenError("No token provided")

        try:
            # Get signing key automatically from JWKS
            signing_key = self.jwks_client.get_signing_key_from_jwt(raw_token)

            # Validate token with Bot Framework requirements
            payload = jwt.decode(
                raw_token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self.app_id,
                issuer="https://api.botframework.com",
                options={
                    "verify_signature": True,
                    "verify_aud": True,
                    "verify_iss": True,
                    "verify_exp": True,
                    "verify_iat": True,
                },
            )

            # Optional service URL validation
            if service_url:
                self._validate_service_url(payload, service_url)

            self.logger.debug("Bot Framework token validation successful")
            return JsonWebToken(value=raw_token)

        except jwt.InvalidTokenError as e:
            self.logger.error(f"Token validation failed: {e}")
            raise

    def _validate_service_url(self, payload: Dict[str, Any], expected_service_url: str) -> None:
        """Validate service URL claim matches expected service URL."""
        token_service_url = payload.get("serviceurl")

        if not token_service_url:
            self.logger.error("Token missing serviceurl claim")
            raise jwt.InvalidTokenError("Token missing serviceurl claim")

        # Normalize URLs (remove trailing slashes)
        normalized_token_url = token_service_url.rstrip("/")
        normalized_expected_url = expected_service_url.rstrip("/")

        if normalized_token_url != normalized_expected_url:
            self.logger.error(
                f"Service URL mismatch. Token: {normalized_token_url}, Expected: {normalized_expected_url}"
            )
            raise jwt.InvalidTokenError(
                f"Service URL mismatch. Token: {normalized_token_url}, Expected: {normalized_expected_url}"
            )
