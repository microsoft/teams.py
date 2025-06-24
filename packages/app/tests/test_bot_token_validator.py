"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import time
from unittest.mock import MagicMock, patch

import pytest
from microsoft.teams.app import (
    BotTokenValidator,
    TokenValidationError,
    TokenValidationErrorCode,
)
from microsoft.teams.app.auth.bot_token_validator import EXPECTED_ISSUER, JwksKey, JwksResponse, OpenIdMetadata


class TestBotTokenValidator:
    """Test cases for BotTokenValidator public interface."""

    @pytest.fixture
    def validator(self):
        """Create BotTokenValidator instance."""
        return BotTokenValidator("test-app-id")

    @pytest.fixture
    def valid_token_payload(self):
        """Create valid token payload."""
        current_time = int(time.time())
        return {
            "iss": EXPECTED_ISSUER,
            "aud": "test-app-id",
            "exp": current_time + 3600,  # Expires in 1 hour
            "iat": current_time,  # Issued now
            "serviceurl": "https://smba.trafficmanager.net/teams",
        }

    @pytest.fixture
    def valid_token_header(self):
        """Create valid token header."""
        return {"alg": "RS256", "kid": "test-key-id", "typ": "JWT"}

    @pytest.fixture
    def mock_openid_metadata(self):
        """Create mock OpenID metadata."""

        return OpenIdMetadata(
            issuer=EXPECTED_ISSUER,
            jwks_uri="https://login.botframework.com/v1/.well-known/jwks",
            id_token_signing_alg_values_supported=["RS256", "RS384", "RS512"],
        )

    @pytest.fixture
    def mock_jwks_response(self):
        """Create mock JWKS response."""

        return JwksResponse(
            keys=[JwksKey(kty="RSA", kid="test-key-id", alg="RS256", use="sig", n="test-modulus", e="AQAB")]
        )

    def test_init_with_app_id(self):
        """Test BotTokenValidator initialization with app ID."""
        validator = BotTokenValidator("test-app-id")

        assert validator.app_id == "test-app-id"
        assert validator.logger is not None
        assert validator.http_client is not None

    def test_init_with_custom_logger(self):
        """Test BotTokenValidator initialization with custom logger."""
        mock_logger = MagicMock()
        validator = BotTokenValidator("test-app-id", mock_logger)

        assert validator.app_id == "test-app-id"
        assert validator.logger == mock_logger

    @pytest.mark.asyncio
    async def test_validate_token_success(
        self, validator, mock_openid_metadata, mock_jwks_response, valid_token_payload, valid_token_header
    ):
        """Test successful token validation through public interface."""
        token = "mock.jwt.token"

        with (
            patch.object(validator, "_get_openid_metadata", return_value=mock_openid_metadata),
            patch.object(validator, "_get_jwks", return_value=mock_jwks_response),
            patch.object(validator, "_jwk_to_key", return_value="mock-key"),
            patch("jwt.decode", return_value=valid_token_payload),
            patch("jwt.get_unverified_header", return_value=valid_token_header),
        ):
            result = await validator.validate_token(token, "https://smba.trafficmanager.net/teams")
            assert result == valid_token_payload

    @pytest.mark.asyncio
    async def test_validate_token_empty_token(self, validator):
        """Test validation with empty token."""
        with pytest.raises(TokenValidationError) as exc_info:
            await validator.validate_token("")
        assert exc_info.value.code == TokenValidationErrorCode.MISSING_TOKEN

    @pytest.mark.asyncio
    async def test_validate_token_none_token(self, validator):
        """Test validation with None token."""
        with pytest.raises(TokenValidationError) as exc_info:
            await validator.validate_token(None)
        assert exc_info.value.code == TokenValidationErrorCode.MISSING_TOKEN

    @pytest.mark.asyncio
    async def test_validate_token_malformed_token(self, validator):
        """Test validation with malformed token."""
        import jwt as pyjwt

        with patch("jwt.get_unverified_header", side_effect=pyjwt.DecodeError("Malformed token")):
            with pytest.raises(TokenValidationError) as exc_info:
                await validator.validate_token("malformed.token")
            assert exc_info.value.code == TokenValidationErrorCode.MALFORMED_TOKEN

    @pytest.mark.asyncio
    async def test_validate_token_invalid_issuer(self, validator, valid_token_payload, valid_token_header):
        """Test validation with invalid issuer."""
        valid_token_payload["iss"] = "invalid-issuer"
        token = "mock.jwt.token"

        with (
            patch("jwt.get_unverified_header", return_value=valid_token_header),
            patch("jwt.decode", return_value=valid_token_payload),
        ):
            with pytest.raises(TokenValidationError) as exc_info:
                await validator.validate_token(token)
            assert exc_info.value.code == TokenValidationErrorCode.INVALID_ISSUER

    @pytest.mark.asyncio
    async def test_validate_token_invalid_audience(self, validator, valid_token_payload, valid_token_header):
        """Test validation with invalid audience."""
        valid_token_payload["aud"] = "wrong-app-id"
        token = "mock.jwt.token"

        with (
            patch("jwt.get_unverified_header", return_value=valid_token_header),
            patch("jwt.decode", return_value=valid_token_payload),
        ):
            with pytest.raises(TokenValidationError) as exc_info:
                await validator.validate_token(token)
            assert exc_info.value.code == TokenValidationErrorCode.INVALID_AUDIENCE

    @pytest.mark.asyncio
    async def test_validate_token_expired(self, validator, valid_token_payload, valid_token_header):
        """Test validation with expired token."""
        current_time = int(time.time())
        valid_token_payload["exp"] = current_time - 3600  # Expired 1 hour ago
        token = "mock.jwt.token"

        with (
            patch("jwt.get_unverified_header", return_value=valid_token_header),
            patch("jwt.decode", return_value=valid_token_payload),
        ):
            with pytest.raises(TokenValidationError) as exc_info:
                await validator.validate_token(token)
            assert exc_info.value.code == TokenValidationErrorCode.EXPIRED_TOKEN

    @pytest.mark.asyncio
    async def test_validate_token_future_issued_at(self, validator, valid_token_payload, valid_token_header):
        """Test validation with token issued in the future."""
        current_time = int(time.time())
        valid_token_payload["iat"] = current_time + 3600  # Issued 1 hour in the future
        token = "mock.jwt.token"

        with (
            patch("jwt.get_unverified_header", return_value=valid_token_header),
            patch("jwt.decode", return_value=valid_token_payload),
        ):
            with pytest.raises(TokenValidationError) as exc_info:
                await validator.validate_token(token)
            assert exc_info.value.code == TokenValidationErrorCode.FUTURE_TOKEN

    @pytest.mark.asyncio
    async def test_validate_token_missing_expiration(self, validator, valid_token_payload, valid_token_header):
        """Test validation with missing expiration claim."""
        del valid_token_payload["exp"]
        token = "mock.jwt.token"

        with (
            patch("jwt.get_unverified_header", return_value=valid_token_header),
            patch("jwt.decode", return_value=valid_token_payload),
        ):
            with pytest.raises(TokenValidationError) as exc_info:
                await validator.validate_token(token)
            assert exc_info.value.code == TokenValidationErrorCode.MALFORMED_TOKEN

    @pytest.mark.asyncio
    async def test_validate_token_unsupported_algorithm(
        self, validator, mock_openid_metadata, valid_token_payload, valid_token_header
    ):
        """Test validation with unsupported algorithm."""
        valid_token_header["alg"] = "HS256"  # Not in supported algorithms
        token = "mock.jwt.token"

        with (
            patch("jwt.get_unverified_header", return_value=valid_token_header),
            patch("jwt.decode", return_value=valid_token_payload),
            patch.object(validator, "_get_openid_metadata", return_value=mock_openid_metadata),
        ):
            with pytest.raises(TokenValidationError) as exc_info:
                await validator.validate_token(token)
            assert exc_info.value.code == TokenValidationErrorCode.UNSUPPORTED_ALGORITHM

    @pytest.mark.asyncio
    async def test_validate_token_missing_algorithm(self, validator, valid_token_payload):
        """Test validation with missing algorithm in header."""
        header_without_alg = {"kid": "test-key-id", "typ": "JWT"}
        token = "mock.jwt.token"

        with (
            patch("jwt.get_unverified_header", return_value=header_without_alg),
            patch("jwt.decode", return_value=valid_token_payload),
        ):
            with pytest.raises(TokenValidationError) as exc_info:
                await validator.validate_token(token)
            assert exc_info.value.code == TokenValidationErrorCode.MALFORMED_TOKEN

    @pytest.mark.asyncio
    async def test_validate_token_missing_key_id(
        self, validator, mock_openid_metadata, valid_token_payload, valid_token_header
    ):
        """Test validation with missing key ID."""
        del valid_token_header["kid"]
        token = "mock.jwt.token"

        with (
            patch("jwt.get_unverified_header", return_value=valid_token_header),
            patch("jwt.decode", return_value=valid_token_payload),
            patch.object(validator, "_get_openid_metadata", return_value=mock_openid_metadata),
        ):
            with pytest.raises(TokenValidationError) as exc_info:
                await validator.validate_token(token)
            assert exc_info.value.code == TokenValidationErrorCode.MISSING_KEY_ID

    @pytest.mark.asyncio
    async def test_validate_token_service_url_mismatch(
        self, validator, mock_openid_metadata, mock_jwks_response, valid_token_payload, valid_token_header
    ):
        """Test validation with service URL mismatch."""
        token = "mock.jwt.token"

        with (
            patch.object(validator, "_get_openid_metadata", return_value=mock_openid_metadata),
            patch.object(validator, "_get_jwks", return_value=mock_jwks_response),
            patch.object(validator, "_jwk_to_key", return_value="mock-key"),
            patch("jwt.decode", return_value=valid_token_payload),
            patch("jwt.get_unverified_header", return_value=valid_token_header),
        ):
            with pytest.raises(TokenValidationError) as exc_info:
                await validator.validate_token(token, "https://different-service.com")
            assert exc_info.value.code == TokenValidationErrorCode.SERVICE_URL_MISMATCH

    @pytest.mark.asyncio
    async def test_validate_token_missing_service_url_claim(
        self, validator, mock_openid_metadata, mock_jwks_response, valid_token_payload, valid_token_header
    ):
        """Test validation with missing service URL claim."""
        del valid_token_payload["serviceurl"]
        token = "mock.jwt.token"

        with (
            patch.object(validator, "_get_openid_metadata", return_value=mock_openid_metadata),
            patch.object(validator, "_get_jwks", return_value=mock_jwks_response),
            patch.object(validator, "_jwk_to_key", return_value="mock-key"),
            patch("jwt.decode", return_value=valid_token_payload),
            patch("jwt.get_unverified_header", return_value=valid_token_header),
        ):
            with pytest.raises(TokenValidationError) as exc_info:
                await validator.validate_token(token, "https://smba.trafficmanager.net/teams")
            assert exc_info.value.code == TokenValidationErrorCode.MISSING_SERVICE_URL

    @pytest.mark.asyncio
    async def test_validate_token_metadata_retrieval_failure(self, validator, valid_token_payload, valid_token_header):
        """Test validation when OpenID metadata retrieval fails."""
        token = "mock.jwt.token"

        with (
            patch("jwt.get_unverified_header", return_value=valid_token_header),
            patch("jwt.decode", return_value=valid_token_payload),
            patch.object(validator, "_get_openid_metadata", return_value=None),
        ):
            with pytest.raises(TokenValidationError) as exc_info:
                await validator.validate_token(token)
            assert exc_info.value.code == TokenValidationErrorCode.METADATA_RETRIEVAL_FAILED

    @pytest.mark.asyncio
    async def test_validate_token_key_retrieval_failure(
        self, validator, mock_openid_metadata, valid_token_payload, valid_token_header
    ):
        """Test validation when public key retrieval fails."""
        token = "mock.jwt.token"

        with (
            patch("jwt.get_unverified_header", return_value=valid_token_header),
            patch("jwt.decode", return_value=valid_token_payload),
            patch.object(validator, "_get_openid_metadata", return_value=mock_openid_metadata),
            patch.object(validator, "_get_public_key", return_value=None),
        ):
            with pytest.raises(TokenValidationError) as exc_info:
                await validator.validate_token(token)
            assert exc_info.value.code == TokenValidationErrorCode.KEY_NOT_FOUND

    @pytest.mark.asyncio
    async def test_validate_token_signature_verification_failure(
        self, validator, mock_openid_metadata, mock_jwks_response, valid_token_payload, valid_token_header
    ):
        """Test validation when JWT signature verification fails."""
        import jwt as pyjwt

        token = "mock.jwt.token"

        with (
            patch("jwt.get_unverified_header", return_value=valid_token_header),
            patch(
                "jwt.decode",
                side_effect=[valid_token_payload, pyjwt.InvalidTokenError("Signature verification failed")],
            ),
            patch.object(validator, "_get_openid_metadata", return_value=mock_openid_metadata),
            patch.object(validator, "_get_jwks", return_value=mock_jwks_response),
            patch.object(validator, "_jwk_to_key", return_value="mock-key"),
        ):
            with pytest.raises(TokenValidationError) as exc_info:
                await validator.validate_token(token)
            assert exc_info.value.code == TokenValidationErrorCode.SIGNATURE_VERIFICATION_FAILED

    @pytest.mark.asyncio
    async def test_validate_token_no_service_url_validation(
        self, validator, mock_openid_metadata, mock_jwks_response, valid_token_payload, valid_token_header
    ):
        """Test successful validation without service URL validation."""
        token = "mock.jwt.token"

        with (
            patch.object(validator, "_get_openid_metadata", return_value=mock_openid_metadata),
            patch.object(validator, "_get_jwks", return_value=mock_jwks_response),
            patch.object(validator, "_jwk_to_key", return_value="mock-key"),
            patch("jwt.decode", return_value=valid_token_payload),
            patch("jwt.get_unverified_header", return_value=valid_token_header),
        ):
            # Don't pass service_url parameter
            result = await validator.validate_token(token)
            assert result == valid_token_payload
