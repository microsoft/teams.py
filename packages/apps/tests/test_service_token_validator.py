"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from unittest.mock import MagicMock, patch

import jwt
import pytest
from microsoft.teams.api import JsonWebToken
from microsoft.teams.apps.auth.service_token_validator import ServiceTokenValidator

# pyright: basic


class TestServiceTokenValidator:
    """Test suite for ServiceTokenValidator."""

    @pytest.fixture
    def validator(self):
        """Create ServiceTokenValidator instance."""
        return ServiceTokenValidator("test-app-id")

    @pytest.fixture
    def mock_signing_key(self):
        """Create mock signing key for PyJWKClient."""
        mock_key = MagicMock()
        mock_key.key = "mock-rsa-key"
        return mock_key

    @pytest.fixture
    def valid_payload(self):
        """Create valid JWT payload."""
        return {
            "iss": "https://api.botframework.com",
            "aud": "test-app-id",
            "serviceurl": "https://smba.trafficmanager.net/teams",
            "exp": 9999999999,  # Far future
            "iat": 1000000000,  # Past timestamp
        }

    def test_init(self):
        """Test ServiceTokenValidator initialization."""
        validator = ServiceTokenValidator("test-app-id")

        assert validator.app_id == "test-app-id"
        assert validator.logger is not None
        assert validator.jwks_client is not None

    def test_init_with_custom_logger(self):
        """Test ServiceTokenValidator initialization with custom logger."""
        mock_logger = MagicMock()
        validator = ServiceTokenValidator("test-app-id", mock_logger)

        assert validator.app_id == "test-app-id"
        assert validator.logger == mock_logger

    @pytest.mark.asyncio
    async def test_validate_token_success(self, validator, mock_signing_key, valid_payload):
        """Test successful token validation."""
        token = "valid.jwt.token"

        with (
            patch.object(validator.jwks_client, "get_signing_key_from_jwt", return_value=mock_signing_key),
            patch("jwt.decode", return_value=valid_payload),
        ):
            result = await validator.validate_token(token)

            assert isinstance(result, JsonWebToken)
            assert str(result) == token

    @pytest.mark.asyncio
    async def test_validate_token_with_service_url(self, validator, mock_signing_key, valid_payload):
        """Test successful token validation with service URL check."""
        token = "valid.jwt.token"
        service_url = "https://smba.trafficmanager.net/teams"

        with (
            patch.object(validator.jwks_client, "get_signing_key_from_jwt", return_value=mock_signing_key),
            patch("jwt.decode", return_value=valid_payload),
        ):
            result = await validator.validate_token(token, service_url)

            assert isinstance(result, JsonWebToken)
            assert str(result) == token

    @pytest.mark.asyncio
    async def test_validate_token_empty_token(self, validator):
        """Test validation with empty token."""
        with pytest.raises(jwt.InvalidTokenError, match="No token provided"):
            await validator.validate_token("")

    @pytest.mark.asyncio
    async def test_validate_token_none_token(self, validator):
        """Test validation with None token."""
        with pytest.raises(jwt.InvalidTokenError, match="No token provided"):
            await validator.validate_token(None)

    @pytest.mark.asyncio
    async def test_validate_token_jwks_error(self, validator):
        """Test validation when JWKS client fails."""
        token = "invalid.jwt.token"

        with patch.object(
            validator.jwks_client,
            "get_signing_key_from_jwt",
            side_effect=jwt.DecodeError("Invalid token format"),
        ):
            with pytest.raises(jwt.InvalidTokenError):
                await validator.validate_token(token)

    @pytest.mark.asyncio
    async def test_validate_token_decode_error(self, validator, mock_signing_key):
        """Test validation when JWT decode fails."""
        token = "invalid.jwt.token"

        with (
            patch.object(validator.jwks_client, "get_signing_key_from_jwt", return_value=mock_signing_key),
            patch("jwt.decode", side_effect=jwt.ExpiredSignatureError("Token expired")),
        ):
            with pytest.raises(jwt.InvalidTokenError):
                await validator.validate_token(token)

    @pytest.mark.asyncio
    async def test_validate_token_invalid_audience(self, validator, mock_signing_key):
        """Test validation with invalid audience."""
        token = "invalid.jwt.token"

        with (
            patch.object(validator.jwks_client, "get_signing_key_from_jwt", return_value=mock_signing_key),
            patch("jwt.decode", side_effect=jwt.InvalidAudienceError("Invalid audience")),
        ):
            with pytest.raises(jwt.InvalidTokenError):
                await validator.validate_token(token)

    @pytest.mark.asyncio
    async def test_validate_token_invalid_issuer(self, validator, mock_signing_key):
        """Test validation with invalid issuer."""
        token = "invalid.jwt.token"

        with (
            patch.object(validator.jwks_client, "get_signing_key_from_jwt", return_value=mock_signing_key),
            patch("jwt.decode", side_effect=jwt.InvalidIssuerError("Invalid issuer")),
        ):
            with pytest.raises(jwt.InvalidTokenError):
                await validator.validate_token(token)

    @pytest.mark.asyncio
    async def test_service_url_validation_missing_claim(self, validator, mock_signing_key):
        """Test service URL validation when token missing serviceurl claim."""
        token = "valid.jwt.token"
        service_url = "https://smba.trafficmanager.net/teams"
        payload_without_service_url = {
            "iss": "https://api.botframework.com",
            "aud": "test-app-id",
        }

        with (
            patch.object(validator.jwks_client, "get_signing_key_from_jwt", return_value=mock_signing_key),
            patch("jwt.decode", return_value=payload_without_service_url),
        ):
            with pytest.raises(jwt.InvalidTokenError, match="Token missing serviceurl claim"):
                await validator.validate_token(token, service_url)

    @pytest.mark.asyncio
    async def test_service_url_validation_mismatch(self, validator, mock_signing_key):
        """Test service URL validation when URLs don't match."""
        token = "valid.jwt.token"
        service_url = "https://smba.trafficmanager.net/teams"
        payload_with_different_url = {
            "iss": "https://api.botframework.com",
            "aud": "test-app-id",
            "serviceurl": "https://different.service.url",
        }

        with (
            patch.object(validator.jwks_client, "get_signing_key_from_jwt", return_value=mock_signing_key),
            patch("jwt.decode", return_value=payload_with_different_url),
        ):
            with pytest.raises(jwt.InvalidTokenError, match="Service URL mismatch"):
                await validator.validate_token(token, service_url)

    @pytest.mark.asyncio
    async def test_service_url_validation_with_trailing_slashes(self, validator, mock_signing_key):
        """Test service URL validation normalizes trailing slashes."""
        token = "valid.jwt.token"
        service_url = "https://smba.trafficmanager.net/teams/"  # With trailing slash
        payload_without_slash = {
            "iss": "https://api.botframework.com",
            "aud": "test-app-id",
            "serviceurl": "https://smba.trafficmanager.net/teams",  # Without trailing slash
        }

        with (
            patch.object(validator.jwks_client, "get_signing_key_from_jwt", return_value=mock_signing_key),
            patch("jwt.decode", return_value=payload_without_slash),
        ):
            # Should succeed because URLs are normalized
            result = await validator.validate_token(token, service_url)
            assert isinstance(result, JsonWebToken)

    def test_validate_service_url_direct(self, validator):
        """Test _validate_service_url method directly."""
        # Test matching URLs
        payload = {"serviceurl": "https://test.com"}
        validator._validate_service_url(payload, "https://test.com")  # Should not raise

        # Test trailing slash normalization
        validator._validate_service_url(payload, "https://test.com/")  # Should not raise

        # Test missing serviceurl
        with pytest.raises(jwt.InvalidTokenError, match="Token missing serviceurl claim"):
            validator._validate_service_url({}, "https://test.com")

        # Test URL mismatch
        with pytest.raises(jwt.InvalidTokenError, match="Service URL mismatch"):
            validator._validate_service_url(payload, "https://different.com")
