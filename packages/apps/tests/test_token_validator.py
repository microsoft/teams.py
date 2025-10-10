"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from unittest.mock import MagicMock, patch

import jwt
import pytest
from microsoft.teams.apps.auth.token_validator import TokenValidator

# pyright: basic


class TestTokenValidator:
    """Test suite for TokenValidator."""

    @pytest.fixture
    def validator(self):
        """Create TokenValidator instance."""
        return TokenValidator.for_service("test-app-id")

    @pytest.fixture
    def validator_entra(self):
        """Create TokenValidator instance for Entra ID."""
        return TokenValidator.for_entra(app_id="test-app-id", tenant_id="test-tenant-id", scope="user.read")

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

    @pytest.fixture
    def valid_payload_entra(self):
        """Valid Entra JWT payload with required scope."""
        return {
            "iss": "https://login.microsoftonline.com/test-tenant-id/v2.0",
            "aud": "test-app-id",
            "scp": "user.read mail.read",
            "exp": 9999999999,
            "iat": 1000000000,
        }

    def test_init(self):
        """Test TokenValidator initialization."""
        validator = TokenValidator.for_service("test-app-id")

        assert validator.logger is not None
        assert validator.options.valid_issuers == ["https://api.botframework.com"]
        assert validator.options.valid_audiences == ["test-app-id", "api://test-app-id"]
        assert validator.options.jwks_uri == "https://login.botframework.com/v1/.well-known/keys"

    def test_init_with_custom_logger(self):
        """Test TokenValidator initialization with custom logger."""
        mock_logger = MagicMock()
        validator = TokenValidator.for_service("test-app-id", mock_logger)

        assert validator.options.valid_issuers == ["https://api.botframework.com"]
        assert validator.options.valid_audiences == ["test-app-id", "api://test-app-id"]
        assert validator.options.jwks_uri == "https://login.botframework.com/v1/.well-known/keys"
        assert validator.logger == mock_logger

    @pytest.mark.asyncio
    async def test_validate_token_success(self, validator, mock_signing_key, valid_payload):
        """Test successful token validation."""
        token = "valid.jwt.token"

        with (
            patch("jwt.PyJWKClient", return_value=mock_signing_key),
            patch("jwt.decode", return_value=valid_payload),
        ):
            result = await validator.validate_token(token)

            assert isinstance(result, dict)
            assert result["iss"] == "https://api.botframework.com"
            assert result["aud"] == "test-app-id"

    @pytest.mark.asyncio
    async def test_validate_token_with_service_url(self, validator, mock_signing_key, valid_payload):
        """Test successful token validation with service URL check."""
        token = "valid.jwt.token"
        service_url = "https://smba.trafficmanager.net/teams"

        with (
            patch("jwt.PyJWKClient", return_value=mock_signing_key),
            patch("jwt.decode", return_value=valid_payload),
        ):
            result = await validator.validate_token(token, service_url)

            assert isinstance(result, dict)
            assert result["iss"] == "https://api.botframework.com"
            assert result["aud"] == "test-app-id"

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

        with patch(
            "jwt.PyJWKClient",
            side_effect=jwt.DecodeError("Invalid token format"),
        ):
            with pytest.raises(jwt.InvalidTokenError):
                await validator.validate_token(token)

    @pytest.mark.asyncio
    async def test_validate_token_decode_error(self, validator, mock_signing_key):
        """Test validation when JWT decode fails."""
        token = "invalid.jwt.token"

        with (
            patch("jwt.PyJWKClient", return_value=mock_signing_key),
            patch("jwt.decode", side_effect=jwt.ExpiredSignatureError("Token expired")),
        ):
            with pytest.raises(jwt.InvalidTokenError):
                await validator.validate_token(token)

    @pytest.mark.asyncio
    async def test_validate_token_invalid_audience(self, validator, mock_signing_key):
        """Test validation with invalid audience."""
        token = "invalid.jwt.token"

        with (
            patch("jwt.PyJWKClient", return_value=mock_signing_key),
            patch("jwt.decode", side_effect=jwt.InvalidAudienceError("Invalid audience")),
        ):
            with pytest.raises(jwt.InvalidTokenError):
                await validator.validate_token(token)

    @pytest.mark.asyncio
    async def test_validate_token_invalid_issuer(self, validator, mock_signing_key):
        """Test validation with invalid issuer."""
        token = "invalid.jwt.token"

        with (
            patch("jwt.PyJWKClient", return_value=mock_signing_key),
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
            patch("jwt.PyJWKClient", return_value=mock_signing_key),
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
            patch("jwt.PyJWKClient", return_value=mock_signing_key),
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
            patch("jwt.PyJWKClient", return_value=mock_signing_key),
            patch("jwt.decode", return_value=payload_without_slash),
        ):
            # Should succeed because URLs are normalized
            result = await validator.validate_token(token, service_url)
            assert isinstance(result, dict)
            assert result["iss"] == "https://api.botframework.com"
            assert result["aud"] == "test-app-id"

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

    def test_for_entra_initialization(self, validator_entra):
        """Check Entra-specific initialization."""
        options = validator_entra.options
        assert options.valid_issuers == ["https://login.microsoftonline.com/test-tenant-id/v2.0"]
        assert options.valid_audiences == ["test-app-id", "api://test-app-id"]
        assert options.jwks_uri == "https://login.microsoftonline.com/test-tenant-id/discovery/v2.0/keys"
        assert options.scope == "user.read"

    @pytest.mark.asyncio
    async def test_validate_entra_token_success_with_scope(
        self, validator_entra, mock_signing_key, valid_payload_entra
    ):
        """Validate Entra token successfully with required scope."""
        token = "entra.valid.token"
        with (
            patch("jwt.PyJWKClient", return_value=mock_signing_key),
            patch("jwt.decode", return_value=valid_payload_entra),
        ):
            payload = await validator_entra.validate_token(token)
            assert payload["scp"] == "user.read mail.read"

    @pytest.mark.asyncio
    async def test_validate_entra_token_missing_scope(self, validator_entra, mock_signing_key):
        """Fail validation if required scope is missing."""
        token = "entra.missing.scope"
        payload_missing_scope = {
            "iss": "https://login.microsoftonline.com/test-tenant-id/v2.0",
            "aud": "test-app-id",
            "scp": "mail.read",
            "exp": 9999999999,
            "iat": 1000000000,
        }

        with (
            patch("jwt.PyJWKClient", return_value=mock_signing_key),
            patch("jwt.decode", return_value=payload_missing_scope),
        ):
            with pytest.raises(jwt.InvalidTokenError, match="Token missing required scope: user.read"):
                await validator_entra.validate_token(token)

    @pytest.mark.asyncio
    async def test_validate_entra_token_invalid_issuer(self, validator_entra, mock_signing_key):
        """Fail validation for invalid issuer."""
        token = "entra.invalid.issuer"
        payload_invalid_issuer = {
            "iss": "https://login.microsoftonline.com/other-tenant/v2.0",
            "aud": "test-app-id",
            "scp": "user.read",
            "exp": 9999999999,
            "iat": 1000000000,
        }

        with (
            patch("jwt.PyJWKClient", return_value=mock_signing_key),
            patch(
                "jwt.decode", return_value=payload_invalid_issuer, side_effect=jwt.InvalidIssuerError("Invalid issuer")
            ),
        ):
            with pytest.raises(jwt.InvalidTokenError):
                await validator_entra.validate_token(token)

    @pytest.mark.asyncio
    async def test_validate_entra_token_invalid_audience(self, validator_entra, mock_signing_key):
        """Fail validation for invalid audience."""
        token = "entra.invalid.aud"
        payload_invalid_aud = {
            "iss": "https://login.microsoftonline.com/test-tenant-id/v2.0",
            "aud": "wrong-app-id",
            "scp": "user.read",
            "exp": 9999999999,
            "iat": 1000000000,
        }

        with (
            patch("jwt.PyJWKClient", return_value=mock_signing_key),
            patch(
                "jwt.decode", return_value=payload_invalid_aud, side_effect=jwt.InvalidAudienceError("Invalid audience")
            ),
        ):
            with pytest.raises(jwt.InvalidTokenError):
                await validator_entra.validate_token(token)
