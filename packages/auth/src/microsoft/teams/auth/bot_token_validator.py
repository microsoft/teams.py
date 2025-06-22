"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import time
from enum import Enum
from typing import Any, Dict, Optional

import jwt
from jwt.algorithms import get_default_algorithms
from microsoft.teams.common.http import Client
from microsoft.teams.common.logging import ConsoleLogger
from pydantic import BaseModel, ConfigDict


class TokenValidationErrorCode(Enum):
    """Error codes for token validation failures."""

    MISSING_TOKEN = "missing_token"
    MALFORMED_TOKEN = "malformed_token"
    EXPIRED_TOKEN = "expired_token"
    FUTURE_TOKEN = "future_token"
    INVALID_ISSUER = "invalid_issuer"
    INVALID_AUDIENCE = "invalid_audience"
    UNSUPPORTED_ALGORITHM = "unsupported_algorithm"
    MISSING_KEY_ID = "missing_key_id"
    KEY_NOT_FOUND = "key_not_found"
    SIGNATURE_VERIFICATION_FAILED = "signature_verification_failed"
    SERVICE_URL_MISMATCH = "service_url_mismatch"
    MISSING_SERVICE_URL = "missing_service_url"
    METADATA_RETRIEVAL_FAILED = "metadata_retrieval_failed"
    JWKS_RETRIEVAL_FAILED = "jwks_retrieval_failed"


class TokenValidationError(Exception):
    """Base exception for token validation failures."""

    def __init__(self, code: TokenValidationErrorCode, message: str):
        self.code = code
        self.message = message
        super().__init__(f"{code.value}: {message}")


class TokenFormatError(TokenValidationError):
    """Raised when token format is invalid."""

    pass


class TokenClaimsError(TokenValidationError):
    """Raised when token claims validation fails."""

    pass


class TokenAuthenticationError(TokenValidationError):
    """Raised when token authentication fails."""

    pass


class TokenInfrastructureError(TokenValidationError):
    """Raised when token validation infrastructure fails."""

    pass


CACHE_TTL = 3600  # 1 hour cache TTL for JWKS and metadata
OPEN_ID_CONFIG_URL = "https://login.botframework.com/v1/.well-known/openidconfiguration"
EXPECTED_ISSUER = "https://api.botframework.com"
EXPIRATION_BUFFER_SECONDS = 300  # 5 minutes buffer for expiration check


class OpenIdMetadata(BaseModel):
    """OpenID Connect metadata for Bot Framework."""

    model_config = ConfigDict(extra="allow")

    issuer: Optional[str] = None
    authorization_endpoint: Optional[str] = None
    jwks_uri: Optional[str] = None
    id_token_signing_alg_values_supported: list[str] = []
    token_endpoint_auth_methods_supported: list[str] = []


class JwksKey(BaseModel):
    """JSON Web Key (JWK) representation for Bot Framework."""

    model_config = ConfigDict(extra="allow")

    kty: Optional[str] = None  # Key type
    kid: Optional[str] = None  # Key ID
    alg: Optional[str] = None  # Algorithm
    use: Optional[str] = None  # Key usage (e.g., sig for signature)
    endorsements: Optional[list[str]] = None  # Endorsements for the key


class JwksResponse(BaseModel):
    """Response containing JSON Web Key Set (JWKS) for Bot Framework."""

    model_config = ConfigDict(extra="allow")

    keys: list[JwksKey] = []  # List of JWKs


class BotTokenValidator:
    """
    Bot Framework JWT token validator following Microsoft's authentication protocol.

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

        self.http_client = Client()

        # Cache for public keys and metadata
        self._jwks_cache: Optional[JwksResponse] = None
        self._jwks_cache_expiry: float = 0.0
        self._metadata_cache: Optional[OpenIdMetadata] = None
        self._metadata_cache_expiry: float = 0.0

    async def validate_token(self, raw_token: str, service_url: Optional[str] = None) -> Any:
        """
        Validate a Bot Framework JWT token.

        Args:
            raw_token: The raw JWT token string
            service_url: Optional service URL to validate against token claims

        Returns:
            Token payload if valid

        Raises:
            TokenFormatError: When token format is invalid
            TokenClaimsError: When token claims validation fails
            TokenAuthenticationError: When token authentication fails
            TokenInfrastructureError: When validation infrastructure fails
        """
        if not raw_token:
            self.logger.error("No token provided")
            raise TokenFormatError(TokenValidationErrorCode.MISSING_TOKEN, "No token provided")

        try:
            # Step 1: Decode token without verification to get header
            unverified_header = jwt.get_unverified_header(raw_token)
            unverified_payload = jwt.decode(raw_token, options={"verify_signature": False})
        except jwt.DecodeError as e:
            self.logger.error(f"Token malformed: {e}")
            raise TokenFormatError(TokenValidationErrorCode.MALFORMED_TOKEN, "Token malformed") from e

        # Step 2: Basic claim validation
        self._validate_basic_claims(unverified_payload)

        # Step 3: Validate algorithm against OpenID metadata
        algorithm = unverified_header.get("alg")
        if not algorithm:
            self.logger.error("Token missing algorithm in header")
            raise TokenFormatError(TokenValidationErrorCode.MALFORMED_TOKEN, "Token missing algorithm in header")

        metadata = await self._get_openid_metadata()
        if not metadata:
            self.logger.error("Failed to retrieve OpenID metadata for algorithm validation")
            raise TokenInfrastructureError(
                TokenValidationErrorCode.METADATA_RETRIEVAL_FAILED, "Failed to retrieve OpenID metadata"
            )

        supported_algorithms = metadata.id_token_signing_alg_values_supported
        if algorithm not in supported_algorithms:
            self.logger.error(f"Token algorithm '{algorithm}' not in supported algorithms: {supported_algorithms}")
            raise TokenAuthenticationError(
                TokenValidationErrorCode.UNSUPPORTED_ALGORITHM, f"Algorithm '{algorithm}' not supported"
            )

        # Step 4: Get public key for signature verification
        public_key_jwk = await self._get_public_key(metadata, unverified_header.get("kid"), algorithm)
        if not public_key_jwk:
            self.logger.error("Failed to retrieve public key for token validation")
            raise TokenAuthenticationError(TokenValidationErrorCode.KEY_NOT_FOUND, "Failed to retrieve public key")

        # Step 5: Verify signature and claims using the validated algorithm
        try:
            verified_payload = jwt.decode(
                raw_token,
                public_key_jwk,
                algorithms=[algorithm],
                audience=self.app_id,
                issuer=EXPECTED_ISSUER,
                options={
                    "verify_signature": True,
                    "verify_aud": True,
                    "verify_iss": True,
                    "verify_exp": True,
                    "verify_iat": True,
                },
            )
        except jwt.InvalidTokenError as e:
            self.logger.error(f"JWT signature verification failed: {e}")
            raise TokenAuthenticationError(
                TokenValidationErrorCode.SIGNATURE_VERIFICATION_FAILED, "Signature verification failed"
            ) from e

        # Step 6: Validate service URL if provided
        if service_url:
            self._validate_service_url(verified_payload, service_url)

        self.logger.debug("Bot Framework token validation successful")
        return verified_payload

    def _validate_basic_claims(self, payload: Dict[str, Any]) -> None:
        """Validate basic token claims."""

        # Check issuer
        if payload.get("iss") != EXPECTED_ISSUER:
            self.logger.error(f"Invalid issuer: {payload.get('iss')}")
            raise TokenClaimsError(TokenValidationErrorCode.INVALID_ISSUER, f"Invalid issuer: {payload.get('iss')}")

        # Check audience
        if payload.get("aud") != self.app_id:
            self.logger.error(f"Invalid audience: {payload.get('aud')}")
            raise TokenClaimsError(TokenValidationErrorCode.INVALID_AUDIENCE, f"Invalid audience: {payload.get('aud')}")

        # Check expiration with 5-minute clock skew
        exp = payload.get("exp")
        if not exp:
            self.logger.error("Token missing expiration claim")
            raise TokenFormatError(TokenValidationErrorCode.MALFORMED_TOKEN, "Token missing expiration claim")

        current_time = time.time()

        if current_time > (exp + EXPIRATION_BUFFER_SECONDS):
            self.logger.error("Token is expired")
            raise TokenClaimsError(TokenValidationErrorCode.EXPIRED_TOKEN, "Token is expired")

        # Check issued at time
        iat = payload.get("iat")
        if iat and (current_time + EXPIRATION_BUFFER_SECONDS) < iat:
            self.logger.error("Token issued in the future")
            raise TokenClaimsError(TokenValidationErrorCode.FUTURE_TOKEN, "Token issued in the future")

    def _validate_service_url(self, payload: Dict[str, Any], expected_service_url: str) -> None:
        """Validate service URL claim matches expected service URL."""
        token_service_url = payload.get("serviceurl")

        if not token_service_url:
            self.logger.error("Token missing serviceurl claim")
            raise TokenClaimsError(TokenValidationErrorCode.MISSING_SERVICE_URL, "Token missing serviceurl claim")

        # Normalize URLs (remove trailing slashes)
        normalized_token_url = token_service_url.rstrip("/")
        normalized_expected_url = expected_service_url.rstrip("/")

        if normalized_token_url != normalized_expected_url:
            self.logger.error(
                f"Service URL mismatch. Token: {normalized_token_url}, Expected: {normalized_expected_url}"
            )
            raise TokenClaimsError(
                TokenValidationErrorCode.SERVICE_URL_MISMATCH,
                f"Service URL mismatch. Token: {normalized_token_url}, Expected: {normalized_expected_url}",
            )

    async def _get_public_key(self, open_id_metadata: OpenIdMetadata, kid: Optional[str], algorithm: str) -> Any:
        """Get public key for token verification."""
        if not kid:
            self.logger.error("Token missing key ID (kid)")
            raise TokenFormatError(TokenValidationErrorCode.MISSING_KEY_ID, "Token missing key ID (kid)")

        # Get JWKS
        jwks = await self._get_jwks(open_id_metadata)
        if not jwks:
            raise TokenInfrastructureError(TokenValidationErrorCode.JWKS_RETRIEVAL_FAILED, "Failed to retrieve JWKS")

        # Find key by kid and validate additional properties
        for key in jwks.keys:
            if key.kid != kid:
                continue

            # Validate algorithm if provided
            if algorithm and key.alg and key.alg != algorithm:
                self.logger.warning(f"Key algorithm mismatch. JWT: {algorithm}, Key: {key.alg} for kid: {kid}")
                continue

            # Validate key usage (should allow signature verification)
            if key.use and key.use != "sig":
                self.logger.warning(f"Key not for signatures. Use: {key.use} for kid: {kid}")
                continue

            # Log endorsements for debugging (Bot Framework specific)
            if key.endorsements:
                self.logger.debug(f"Key {kid} has endorsements: {key.endorsements}")

            # Convert JWK to key object that PyJWT can use
            return self._jwk_to_key(key.model_dump(), algorithm)

        self.logger.error(f"No suitable public key found for kid: {kid}")
        raise TokenAuthenticationError(
            TokenValidationErrorCode.KEY_NOT_FOUND, f"No suitable public key found for kid: {kid}"
        )

    async def _get_jwks(self, open_id_metadata: OpenIdMetadata) -> Optional[JwksResponse]:
        """Get JSON Web Key Set from Bot Framework."""
        current_time = time.time()

        # Return cached JWKS if still valid
        if self._jwks_cache and current_time < self._jwks_cache_expiry:
            return self._jwks_cache

        try:
            # Get OpenID configuration
            jwks_uri = open_id_metadata.jwks_uri
            if not jwks_uri:
                self.logger.error("No jwks_uri in OpenID metadata")
                return None

            # Fetch JWKS
            response = await self.http_client.get(jwks_uri)

            self._jwks_cache = JwksResponse.model_validate(response.json())
            self._jwks_cache_expiry = current_time + CACHE_TTL

            self.logger.debug(f"Retrieved JWKS from {jwks_uri}")
            return self._jwks_cache

        except Exception as e:
            self.logger.error(f"Failed to retrieve JWKS: {e}")
            return None

    async def _get_openid_metadata(self) -> Optional[OpenIdMetadata]:
        """Get OpenID Connect metadata from Bot Framework."""
        current_time = time.time()

        # Return cached metadata if still valid
        if self._metadata_cache and current_time < self._metadata_cache_expiry:
            return self._metadata_cache

        try:
            response = await self.http_client.get(OPEN_ID_CONFIG_URL)

            self._metadata_cache = OpenIdMetadata.model_validate(response.json())
            self._metadata_cache_expiry = current_time + CACHE_TTL

            self.logger.debug(f"Retrieved OpenID metadata from {OPEN_ID_CONFIG_URL}")
            return self._metadata_cache

        except Exception as e:
            self.logger.error(f"Failed to retrieve OpenID metadata: {e}")
            return None

    def _jwk_to_key(self, jwk: Dict[str, Any], algorithm: str) -> Optional[Any]:
        """Convert JWK to a key object that PyJWT can use it"""
        try:
            # Use the specific algorithm from the JWT header
            algorithms = get_default_algorithms()

            if algorithm not in algorithms:
                self.logger.error(f"Algorithm {algorithm} not supported")
                return None

            # Convert JWK using the specific algorithm
            return algorithms[algorithm].from_jwk(jwk)

        except Exception as e:
            self.logger.error(f"Failed to convert JWK to key using algorithm {algorithm}: {e}")
            return None
