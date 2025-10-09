"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from dataclasses import dataclass
from logging import Logger
from typing import Any, Dict, List, Optional

import jwt
from microsoft.teams.common.logging import ConsoleLogger

JWT_LEEWAY_SECONDS = 300  # Allowable clock skew when validating JWTs


@dataclass
class JwtValidationOptions:
    """Configuration for JWT validation."""

    valid_issuers: List[str]
    """ List of valid issuers for the JWT"""
    valid_audiences: List[str]
    """ List of valid audiences for the JWT"""
    jwks_uri: str
    """ URI to the JSON Web Key Set (JWKS) for token signature verification """
    service_url: Optional[str] = None
    """ Optional service URL to validate against token claims """
    scope: Optional[str] = None
    """ Optional scope that must be present in the token """
    clock_tolerance: int = JWT_LEEWAY_SECONDS
    """ Allowable clock skew when validating JWTs """


class TokenValidator:
    """
    JWT token validator using PyJWKClient for simplified validation.
    """

    def __init__(self, jwt_validation_options: JwtValidationOptions, logger: Optional[Logger] = None):
        """
        Initialize the token validator.

        Args:
            jwt_validation_options: Configuration for JWT validation
        """
        self.logger = logger or ConsoleLogger().create_logger("@teams/token-validator")
        self.options = jwt_validation_options

    # ----- Factory constructors -----
    @classmethod
    def for_service(
        cls, app_id: str, logger: Optional[Logger] = None, service_url: Optional[str] = None
    ) -> "TokenValidator":
        """Create a validator for Bot Framework service tokens.

        Reference: https://learn.microsoft.com/en-us/azure/bot-service/rest-api/bot-framework-rest-connector-authentication

        Args:
            app_id: The bot's Microsoft App ID (used for audience validation)
            service_url: Optional service URL to validate against token claims
            logger: Optional logger instance"""

        options = JwtValidationOptions(
            valid_issuers=["https://api.botframework.com"],
            valid_audiences=[app_id, f"api://{app_id}"],
            jwks_uri="https://login.botframework.com/v1/.well-known/keys",
            service_url=service_url,
        )
        return cls(options, logger)

    @classmethod
    def for_entra(
        cls, app_id: str, tenant_id: Optional[str], scope: Optional[str] = None, logger: Optional[Logger] = None
    ) -> "TokenValidator":
        """Create a validator for Entra ID tokens.

        Args:
            app_id: The app's Microsoft App ID (used for audience validation)
            tenant_id: The Azure AD tenant ID
            scope: Optional scope that must be present in the token
            logger: Optional logger instance

        """

        valid_issuers: List[str] = []
        if tenant_id:
            valid_issuers.append(f"https://login.microsoftonline.com/{tenant_id}/v2.0")
        tenant_id = tenant_id or "common"
        options = JwtValidationOptions(
            valid_issuers=valid_issuers,
            valid_audiences=[app_id, f"api://{app_id}"],
            jwks_uri=f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys",
            scope=scope,
        )
        return cls(options, logger)

    async def validate_token(
        self, raw_token: str, service_url: Optional[str] = None, scope: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate a JWT token.

        Args:
            raw_token: The raw JWT token string
            service_url: Optional service URL to validate against token claims
            scope: Optional scope that must be present in the token

        Returns:
            The decoded JWT payload if validation is successful

        Raises:
            jwt.InvalidTokenError: When token validation fails
        """
        if not raw_token:
            self.logger.error("No token provided")
            raise jwt.InvalidTokenError("No token provided")

        try:
            jwks_client = jwt.PyJWKClient(self.options.jwks_uri)
            # Get signing key automatically from JWKS
            signing_key = jwks_client.get_signing_key_from_jwt(raw_token)

            # Validate token
            payload: Dict[str, Any] = jwt.decode(
                raw_token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self.options.valid_audiences,
                issuer=self.options.valid_issuers,
                options={
                    "verify_signature": True,
                    "verify_aud": True,
                    "verify_iss": bool(self.options.valid_issuers),
                    "verify_exp": True,
                    "verify_iat": True,
                },
                leeway=JWT_LEEWAY_SECONDS,
            )

            # Optional service URL validation
            expected_service_url = service_url or self.options.service_url
            if expected_service_url:
                self._validate_service_url(payload, expected_service_url)

            required_scope = scope or self.options.scope
            if required_scope:
                self._validate_scope(payload, required_scope)

            self.logger.debug("Token validation successful")
            return payload

        except jwt.InvalidTokenError as e:
            self.logger.error(f"Token validation failed: {e}")
            raise

    def _validate_service_url(self, payload: Dict[str, Any], expected_service_url: str) -> None:
        """Validate service URL claim matches expected service URL.

        Args:
            payload: The decoded JWT payload
            expected_service_url: The service URL to validate against
        """
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

    def _validate_scope(self, payload: Dict[str, Any], required_scope: str) -> None:
        """Validate that the required scope is present in the token.

        Args:
            payload: The decoded JWT payload
            required_scope: The scope required to be present in the token
        """
        scopes = payload.get("scp", "") or ""
        if required_scope not in scopes:
            self.logger.error(f"Token missing required scope: {required_scope}")
            raise jwt.InvalidTokenError(f"Token missing required scope: {required_scope}")
