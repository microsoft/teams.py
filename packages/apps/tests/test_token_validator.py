"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from microsoft_teams.apps.auth.token_validator import (
    MAX_ENTRA_VALIDATOR_CACHE_SIZE,
    InboundActivityTokenValidator,
    TokenValidator,
)

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
    def mock_jwks_client(self, mock_signing_key):
        """Create mock PyJWKClient that returns the mock signing key."""
        client = MagicMock()
        client.get_signing_key_from_jwt.return_value = mock_signing_key
        return client

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

        assert validator.options.valid_issuers == ["https://api.botframework.com"]
        assert validator.options.valid_audiences == [
            "test-app-id",
            "api://test-app-id",
            "api://botid-test-app-id",
        ]
        assert validator.options.jwks_uri == "https://login.botframework.com/v1/.well-known/keys"

    @pytest.mark.asyncio
    async def test_validate_token_success(self, validator, mock_jwks_client, valid_payload):
        """Test successful token validation."""
        token = "valid.jwt.token"

        validator._jwks_client = mock_jwks_client
        with patch("jwt.decode", return_value=valid_payload):
            result = await validator.validate_token(token)

            assert isinstance(result, dict)
            assert result["iss"] == "https://api.botframework.com"
            assert result["aud"] == "test-app-id"

    @pytest.mark.asyncio
    async def test_validate_token_with_service_url(self, validator, mock_jwks_client, valid_payload):
        """Test successful token validation with service URL check."""
        token = "valid.jwt.token"
        service_url = "https://smba.trafficmanager.net/teams"

        validator._jwks_client = mock_jwks_client
        with patch("jwt.decode", return_value=valid_payload):
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

        mock_client = MagicMock()
        mock_client.get_signing_key_from_jwt.side_effect = jwt.DecodeError("Invalid token format")
        validator._jwks_client = mock_client
        with pytest.raises(jwt.InvalidTokenError):
            await validator.validate_token(token)

    @pytest.mark.asyncio
    async def test_validate_token_decode_error(self, validator, mock_jwks_client):
        """Test validation when JWT decode fails."""
        token = "invalid.jwt.token"

        validator._jwks_client = mock_jwks_client
        with patch("jwt.decode", side_effect=jwt.ExpiredSignatureError("Token expired")):
            with pytest.raises(jwt.InvalidTokenError):
                await validator.validate_token(token)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "audience",
        [
            "test-app-id",
            "api://test-app-id",
            "api://botid-test-app-id",
        ],
        ids=["app_id", "api://app_id", "api://botid-app_id"],
    )
    async def test_validate_token_accepts_all_audience_formats(self, mock_jwks_client, audience):
        """Test that all three audience formats are accepted."""
        validator = TokenValidator.for_service("test-app-id")
        validator._jwks_client = mock_jwks_client
        token = "valid.jwt.token"
        payload = {
            "iss": "https://api.botframework.com",
            "aud": audience,
            "serviceurl": "https://smba.trafficmanager.net/teams",
            "exp": 9999999999,
            "iat": 1000000000,
        }

        with patch("jwt.decode", return_value=payload):
            result = await validator.validate_token(token)
            assert result["aud"] == audience

    @pytest.mark.asyncio
    async def test_validate_token_invalid_audience(self, validator, mock_jwks_client):
        """Test validation with invalid audience."""
        token = "invalid.jwt.token"

        validator._jwks_client = mock_jwks_client
        with patch("jwt.decode", side_effect=jwt.InvalidAudienceError("Invalid audience")):
            with pytest.raises(jwt.InvalidTokenError):
                await validator.validate_token(token)

    @pytest.mark.asyncio
    async def test_validate_token_invalid_issuer(self, validator, mock_jwks_client):
        """Test validation with invalid issuer."""
        token = "invalid.jwt.token"

        validator._jwks_client = mock_jwks_client
        with patch("jwt.decode", side_effect=jwt.InvalidIssuerError("Invalid issuer")):
            with pytest.raises(jwt.InvalidTokenError):
                await validator.validate_token(token)

    @pytest.mark.asyncio
    async def test_service_url_validation_missing_claim(self, validator, mock_jwks_client):
        """Test service URL validation when token missing serviceurl claim."""
        token = "valid.jwt.token"
        service_url = "https://smba.trafficmanager.net/teams"
        payload_without_service_url = {
            "iss": "https://api.botframework.com",
            "aud": "test-app-id",
        }

        validator._jwks_client = mock_jwks_client
        with patch("jwt.decode", return_value=payload_without_service_url):
            with pytest.raises(jwt.InvalidTokenError, match="Token missing serviceurl claim"):
                await validator.validate_token(token, service_url)

    @pytest.mark.asyncio
    async def test_service_url_validation_mismatch(self, validator, mock_jwks_client):
        """Test service URL validation when URLs don't match."""
        token = "valid.jwt.token"
        service_url = "https://smba.trafficmanager.net/teams"
        payload_with_different_url = {
            "iss": "https://api.botframework.com",
            "aud": "test-app-id",
            "serviceurl": "https://different.service.url",
        }

        validator._jwks_client = mock_jwks_client
        with patch("jwt.decode", return_value=payload_with_different_url):
            with pytest.raises(jwt.InvalidTokenError, match="Service URL mismatch"):
                await validator.validate_token(token, service_url)

    @pytest.mark.asyncio
    async def test_service_url_validation_with_trailing_slashes(self, validator, mock_jwks_client):
        """Test service URL validation normalizes trailing slashes."""
        token = "valid.jwt.token"
        service_url = "https://smba.trafficmanager.net/teams/"  # With trailing slash
        payload_without_slash = {
            "iss": "https://api.botframework.com",
            "aud": "test-app-id",
            "serviceurl": "https://smba.trafficmanager.net/teams",  # Without trailing slash
        }

        validator._jwks_client = mock_jwks_client
        with patch("jwt.decode", return_value=payload_without_slash):
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
        assert options.valid_issuers == [
            "https://login.microsoftonline.com/test-tenant-id/v2.0",
            "https://sts.windows.net/test-tenant-id/",
        ]
        assert options.valid_audiences == ["test-app-id", "api://test-app-id", "api://botid-test-app-id"]
        assert options.jwks_uri == "https://login.microsoftonline.com/test-tenant-id/discovery/v2.0/keys"
        assert options.scope == "user.read"

    @pytest.mark.asyncio
    async def test_validate_entra_token_success_with_scope(
        self, validator_entra, mock_jwks_client, valid_payload_entra
    ):
        """Validate Entra token successfully with required scope."""
        token = "entra.valid.token"
        validator_entra._jwks_client = mock_jwks_client
        with patch("jwt.decode", return_value=valid_payload_entra):
            payload = await validator_entra.validate_token(token)
            assert payload["scp"] == "user.read mail.read"

    @pytest.mark.asyncio
    async def test_validate_entra_token_missing_scope(self, validator_entra, mock_jwks_client):
        """Fail validation if required scope is missing."""
        token = "entra.missing.scope"
        payload_missing_scope = {
            "iss": "https://login.microsoftonline.com/test-tenant-id/v2.0",
            "aud": "test-app-id",
            "scp": "mail.read",
            "exp": 9999999999,
            "iat": 1000000000,
        }

        validator_entra._jwks_client = mock_jwks_client
        with patch("jwt.decode", return_value=payload_missing_scope):
            with pytest.raises(jwt.InvalidTokenError, match="Token missing required scope: user.read"):
                await validator_entra.validate_token(token)

    @pytest.mark.asyncio
    async def test_validate_entra_token_invalid_issuer(self, validator_entra, mock_jwks_client):
        """Fail validation for invalid issuer."""
        token = "entra.invalid.issuer"
        payload_invalid_issuer = {
            "iss": "https://login.microsoftonline.com/other-tenant/v2.0",
            "aud": "test-app-id",
            "scp": "user.read",
            "exp": 9999999999,
            "iat": 1000000000,
        }

        validator_entra._jwks_client = mock_jwks_client
        with patch(
            "jwt.decode", return_value=payload_invalid_issuer, side_effect=jwt.InvalidIssuerError("Invalid issuer")
        ):
            with pytest.raises(jwt.InvalidTokenError):
                await validator_entra.validate_token(token)

    def test_for_entra_with_application_id_uri(self):
        """Check that applicationIdUri is included in valid audiences."""
        validator = TokenValidator.for_entra(
            app_id="test-app-id",
            tenant_id="test-tenant-id",
            application_id_uri="api://my-app.contoso.com/test-app-id",
        )
        options = validator.options
        assert "api://my-app.contoso.com/test-app-id" in options.valid_audiences

    def test_for_entra_without_application_id_uri(self):
        """Check that audiences are default when applicationIdUri is not provided."""
        validator = TokenValidator.for_entra(app_id="test-app-id", tenant_id="test-tenant-id")
        options = validator.options
        assert options.valid_audiences == ["test-app-id", "api://test-app-id", "api://botid-test-app-id"]

    @pytest.mark.asyncio
    async def test_validate_entra_token_invalid_audience(self, validator_entra, mock_jwks_client):
        """Fail validation for invalid audience."""
        token = "entra.invalid.aud"
        payload_invalid_aud = {
            "iss": "https://login.microsoftonline.com/test-tenant-id/v2.0",
            "aud": "wrong-app-id",
            "scp": "user.read",
            "exp": 9999999999,
            "iat": 1000000000,
        }

        validator_entra._jwks_client = mock_jwks_client
        with patch(
            "jwt.decode", return_value=payload_invalid_aud, side_effect=jwt.InvalidAudienceError("Invalid audience")
        ):
            with pytest.raises(jwt.InvalidTokenError):
                await validator_entra.validate_token(token)

    # --- Finding 4: Scope validation uses exact match, not substring ---

    @pytest.mark.asyncio
    async def test_scope_validation_rejects_substring_match(self, mock_jwks_client):
        """Scope 'User.Read' should NOT match 'User.ReadBasic.All' (substring)."""
        validator = TokenValidator.for_entra(app_id="test-app-id", tenant_id="test-tenant-id", scope="User.Read")
        validator._jwks_client = mock_jwks_client
        payload = {
            "iss": "https://login.microsoftonline.com/test-tenant-id/v2.0",
            "aud": "test-app-id",
            "scp": "User.ReadBasic.All",
            "exp": 9999999999,
            "iat": 1000000000,
        }

        with patch("jwt.decode", return_value=payload):
            with pytest.raises(jwt.InvalidTokenError, match="Token missing required scope: User.Read"):
                await validator.validate_token("valid.jwt.token")

    @pytest.mark.asyncio
    async def test_scope_validation_accepts_exact_match_among_multiple(self, mock_jwks_client):
        """Scope 'User.Read' should match when present among multiple scopes."""
        validator = TokenValidator.for_entra(app_id="test-app-id", tenant_id="test-tenant-id", scope="User.Read")
        validator._jwks_client = mock_jwks_client
        payload = {
            "iss": "https://login.microsoftonline.com/test-tenant-id/v2.0",
            "aud": "test-app-id",
            "scp": "Mail.Read User.Read Files.ReadWrite",
            "exp": 9999999999,
            "iat": 1000000000,
        }

        with patch("jwt.decode", return_value=payload):
            result = await validator.validate_token("valid.jwt.token")
            assert result["scp"] == "Mail.Read User.Read Files.ReadWrite"

    # --- Finding 10: Issuer validation bypass ---

    def test_for_entra_without_tenant_id_logs_warning(self, caplog):
        """Creating Entra validator without tenant_id should log a warning."""
        import logging

        with caplog.at_level(logging.WARNING):
            validator = TokenValidator.for_entra(app_id="test-app-id", tenant_id=None)
            assert validator.options.valid_issuers == []
            assert "Issuer validation will be skipped" in caplog.text

    @pytest.mark.asyncio
    async def test_validate_entra_token_v1_sts_issuer(self, mock_jwks_client):
        """Validator should accept the Azure AD v1 sts.windows.net issuer."""
        validator = TokenValidator.for_entra(app_id="test-app-id", tenant_id="test-tenant-id", scope="user.read")
        validator._jwks_client = mock_jwks_client
        payload_v1 = {
            "iss": "https://sts.windows.net/test-tenant-id/",
            "aud": "test-app-id",
            "scp": "user.read",
            "appid": "test-app-id",
            "tid": "test-tenant-id",
            "ver": "1.0",
            "exp": 9999999999,
            "iat": 1000000000,
        }

        with patch("jwt.decode", return_value=payload_v1):
            result = await validator.validate_token("v1.entra.token")
            assert result["iss"] == "https://sts.windows.net/test-tenant-id/"
            assert result["ver"] == "1.0"


class TestInboundActivityTokenValidator:
    @pytest.mark.asyncio
    async def test_validate_token_uses_service_validator_for_bot_framework_tokens(self):
        validator = InboundActivityTokenValidator("test-app-id")
        validator._service_validator.validate_token = AsyncMock(return_value={"iss": "https://api.botframework.com"})

        with patch("jwt.decode", return_value={"iss": "https://api.botframework.com"}) as decode:
            result = await validator.validate_token("bot-token", "https://service.example")

        assert result == {"iss": "https://api.botframework.com"}
        decode.assert_called_once_with("bot-token", algorithms=["RS256"], options={"verify_signature": False})
        validator._service_validator.validate_token.assert_called_once_with("bot-token", "https://service.example")

    @pytest.mark.asyncio
    async def test_validate_token_uses_entra_validator_for_v2_issuer(self):
        validator = InboundActivityTokenValidator("test-app-id")
        validator._service_validator.validate_token = AsyncMock()
        entra_validator = MagicMock()
        entra_validator.validate_token = AsyncMock(return_value={"tid": "tenant-id"})

        with patch.object(validator, "_get_entra_validator", return_value=entra_validator) as get_validator:
            with patch(
                "jwt.decode",
                return_value={"iss": "https://login.microsoftonline.com/tenant-id/v2.0", "tid": "tenant-id"},
            ):
                result = await validator.validate_token("entra-token", "https://service.example")

        assert result == {"tid": "tenant-id"}
        get_validator.assert_called_once_with("tenant-id")
        entra_validator.validate_token.assert_called_once_with("entra-token")
        validator._service_validator.validate_token.assert_not_called()

    @pytest.mark.asyncio
    async def test_validate_token_uses_entra_validator_for_v1_sts_issuer(self):
        validator = InboundActivityTokenValidator("test-app-id")
        entra_validator = MagicMock()
        entra_validator.validate_token = AsyncMock(return_value={"tid": "tenant-id"})

        with patch.object(validator, "_get_entra_validator", return_value=entra_validator) as get_validator:
            with patch("jwt.decode", return_value={"iss": "https://sts.windows.net/tenant-id/", "tid": "tenant-id"}):
                result = await validator.validate_token("entra-v1-token")

        assert result == {"tid": "tenant-id"}
        get_validator.assert_called_once_with("tenant-id")
        entra_validator.validate_token.assert_called_once_with("entra-v1-token")

    @pytest.mark.asyncio
    async def test_validate_token_rejects_entra_token_without_tid(self):
        validator = InboundActivityTokenValidator("test-app-id")

        with patch("jwt.decode", return_value={"iss": "https://login.microsoftonline.com/tenant-id/v2.0"}):
            with pytest.raises(jwt.InvalidTokenError, match="missing tid"):
                await validator.validate_token("entra-token")

    def test_get_entra_validator_caches_by_tenant(self):
        validator = InboundActivityTokenValidator("test-app-id")

        with patch("microsoft_teams.apps.auth.token_validator.TokenValidator.for_entra") as for_entra:
            for_entra.return_value = MagicMock()

            first = validator._get_entra_validator("tenant-id")
            second = validator._get_entra_validator("tenant-id")

        assert first is second
        for_entra.assert_called_once_with("test-app-id", "tenant-id", cloud=validator._cloud)

    def test_get_entra_validator_cache_is_bounded(self):
        validator = InboundActivityTokenValidator("test-app-id")

        with patch("microsoft_teams.apps.auth.token_validator.TokenValidator.for_entra") as for_entra:
            for_entra.side_effect = lambda _app_id, tenant_id, **_kwargs: MagicMock(name=tenant_id)

            for index in range(MAX_ENTRA_VALIDATOR_CACHE_SIZE + 1):
                validator._get_entra_validator(f"tenant-{index}")

        assert len(validator._entra_validators_by_tenant) == MAX_ENTRA_VALIDATOR_CACHE_SIZE
        assert "tenant-0" not in validator._entra_validators_by_tenant
        assert f"tenant-{MAX_ENTRA_VALIDATOR_CACHE_SIZE}" in validator._entra_validators_by_tenant
