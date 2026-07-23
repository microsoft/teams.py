"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import jwt
from microsoft_teams.api.auth.cloud_environment import PUBLIC, CloudEnvironment

JWT_LEEWAY_SECONDS = 300  # Allowable clock skew when validating JWTs
_MAX_ENTRA_VALIDATOR_CACHE_SIZE = 100
ENTRA_V1_ISSUER_PREFIX = "https://sts.windows.net/"

logger = logging.getLogger(__name__)


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

    def __init__(
        self,
        jwt_validation_options: JwtValidationOptions,
    ):
        """
        Initialize the token validator.

        Args:
            jwt_validation_options: Configuration for JWT validation
        """
        self.options = jwt_validation_options
        self._jwks_client = jwt.PyJWKClient(jwt_validation_options.jwks_uri)

    @staticmethod
    def _default_audiences(app_id: str) -> List[str]:
        return [app_id, f"api://{app_id}", f"api://botid-{app_id}"]

    # ----- Factory constructors -----
    @classmethod
    def for_service(
        cls,
        app_id: str,
        service_url: Optional[str] = None,
        cloud: Optional[CloudEnvironment] = None,
    ) -> TokenValidator:
        """Create a validator for Bot Framework service tokens.

        Reference: https://learn.microsoft.com/en-us/azure/bot-service/rest-api/bot-framework-rest-connector-authentication

        Args:
            app_id: The bot's Microsoft App ID (used for audience validation)
            service_url: Optional service URL to validate against token claims
            cloud: Optional cloud environment for sovereign cloud support
        """
        env = cloud or PUBLIC
        jwks_keys_uri = re.sub(r"/openidconfiguration$", "/keys", env.openid_metadata_url)

        options = JwtValidationOptions(
            valid_issuers=[env.token_issuer],
            valid_audiences=cls._default_audiences(app_id),
            jwks_uri=jwks_keys_uri,
            service_url=service_url,
        )
        return cls(options)

    @classmethod
    def for_entra(
        cls,
        app_id: str,
        tenant_id: Optional[str],
        scope: Optional[str] = None,
        application_id_uri: Optional[str] = None,
        cloud: Optional[CloudEnvironment] = None,
    ) -> TokenValidator:
        """Create a validator for Entra ID tokens.

        Args:
            app_id: The app's Microsoft App ID (used for audience validation)
            tenant_id: The Azure AD tenant ID
            scope: Optional scope that must be present in the token
            application_id_uri: Optional Application ID URI from Azure portal.
                Matches webApplicationInfo.resource in the app manifest.
            cloud: Optional cloud environment for sovereign cloud support
        """
        env = cloud or PUBLIC
        valid_issuers: List[str] = []
        if tenant_id:
            # Accept both Azure AD v2 (login.microsoftonline.com/.../v2.0) and
            # v1 (sts.windows.net/.../) issuer formats. Some valid Entra tokens
            # are still issued with the v1 issuer.
            # See: https://learn.microsoft.com/en-us/entra/identity-platform/access-tokens
            valid_issuers.append(f"{env.login_endpoint}/{tenant_id}/v2.0")
            valid_issuers.append(f"{ENTRA_V1_ISSUER_PREFIX}{tenant_id}/")
        else:
            logger.warning(
                "No tenant_id provided for Entra token validation. "
                "Issuer validation will be skipped, accepting tokens from any tenant."
            )
        tenant_id = tenant_id or "common"
        valid_audiences = cls._default_audiences(app_id)
        if application_id_uri:
            valid_audiences.append(application_id_uri)
        options = JwtValidationOptions(
            valid_issuers=valid_issuers,
            valid_audiences=valid_audiences,
            jwks_uri=f"{env.login_endpoint}/{tenant_id}/discovery/v2.0/keys",
            scope=scope,
        )
        return cls(options)

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
            logger.error("No token provided")
            raise jwt.InvalidTokenError("No token provided")

        try:
            signing_key = self._jwks_client.get_signing_key_from_jwt(raw_token)

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

            # Optional service URL claim validation
            effective_service_url = service_url or self.options.service_url
            if effective_service_url:
                self._validate_service_url(payload, effective_service_url)

            required_scope = scope or self.options.scope
            if required_scope:
                self._validate_scope(payload, required_scope)

            logger.debug("Token validation successful")
            return payload

        except jwt.InvalidTokenError as e:
            logger.error(f"Token validation failed: {e}")
            raise

    def _validate_service_url(self, payload: Dict[str, Any], expected_service_url: str) -> None:
        """Validate service URL claim matches expected service URL.

        Args:
            payload: The decoded JWT payload
            expected_service_url: The service URL to validate against
        """
        token_service_url = payload.get("serviceurl")

        if not token_service_url:
            logger.error("Token missing serviceurl claim")
            raise jwt.InvalidTokenError("Token missing serviceurl claim")

        # Normalize URLs (remove trailing slashes)
        normalized_token_url = token_service_url.rstrip("/")
        normalized_expected_url = expected_service_url.rstrip("/")

        if normalized_token_url != normalized_expected_url:
            logger.error(f"Service URL mismatch. Token: {normalized_token_url}, Expected: {normalized_expected_url}")
            raise jwt.InvalidTokenError(
                f"Service URL mismatch. Token: {normalized_token_url}, Expected: {normalized_expected_url}"
            )

    def _validate_scope(self, payload: Dict[str, Any], required_scope: str) -> None:
        """Validate that the required scope is present in the token.

        Args:
            payload: The decoded JWT payload
            required_scope: The scope required to be present in the token
        """
        scope_set = set((payload.get("scp", "") or "").split())
        if required_scope not in scope_set:
            logger.error(f"Token missing required scope: {required_scope}")
            raise jwt.InvalidTokenError(f"Token missing required scope: {required_scope}")


class InboundActivityTokenValidator:
    """Validator for inbound Teams activities.

    Classic bot activities use Bot Framework connector tokens. Agent ID activities use
    Entra tokens whose audience is the AgenticBlueprint app ID.
    """

    def __init__(self, app_id: str, cloud: Optional[CloudEnvironment] = None):
        self._app_id = app_id
        self._cloud = cloud or PUBLIC
        self._service_validator = TokenValidator.for_service(app_id, cloud=self._cloud)
        self._entra_validators_by_tenant: dict[str, TokenValidator] = {}

    async def validate_token(self, raw_token: str, service_url: Optional[str] = None) -> Dict[str, Any]:
        if not raw_token:
            logger.error("No token provided")
            raise jwt.InvalidTokenError("No token provided")

        unverified_payload = jwt.decode(raw_token, algorithms=["RS256"], options={"verify_signature": False})
        issuer = unverified_payload.get("iss", "")
        if self._is_entra_issuer(issuer):
            return await self._validate_entra_token(raw_token, unverified_payload)

        return await self._service_validator.validate_token(raw_token, service_url)

    def _is_entra_issuer(self, issuer: Any) -> bool:
        if not isinstance(issuer, str):
            return False

        return issuer.startswith(self._cloud.login_endpoint) or issuer.startswith(ENTRA_V1_ISSUER_PREFIX)

    async def _validate_entra_token(self, raw_token: str, unverified_payload: Dict[str, Any]) -> Dict[str, Any]:
        tenant_id = unverified_payload.get("tid")
        if not tenant_id or not isinstance(tenant_id, str):
            raise jwt.InvalidTokenError("Entra inbound token is missing tid")

        validator = self._get_entra_validator(tenant_id)
        # TODO: Agent ID inbound Entra tokens currently do not include serviceurl. Revisit service URL
        # validation for this path once the platform defines a signed service URL claim or equivalent.
        return await validator.validate_token(raw_token)

    def _get_entra_validator(self, tenant_id: str) -> TokenValidator:
        cached_validator = self._entra_validators_by_tenant.get(tenant_id)
        if cached_validator:
            return cached_validator

        validator = TokenValidator.for_entra(
            self._app_id,
            tenant_id,
            cloud=self._cloud,
        )
        self._entra_validators_by_tenant[tenant_id] = validator
        if len(self._entra_validators_by_tenant) > _MAX_ENTRA_VALIDATOR_CACHE_SIZE:
            oldest_tenant_id = next(iter(self._entra_validators_by_tenant))
            self._entra_validators_by_tenant.pop(oldest_tenant_id)
        return validator
