"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any

import jwt
from microsoft.teams.api.auth import CallerIds, JsonWebToken


def build_token(token_payload: dict[str, Any]) -> str:
    secret_key = "test_key"
    return jwt.encode(token_payload, secret_key, algorithm="HS256")


class TestJsonWebToken:
    """Test cases for JsonWebToken class."""

    def test_should_be_from_bot(self):
        """Test JWT token identified as bot caller."""
        token_payload = {
            "kid": "456",
            "appid": "test",
            "tid": "789",
            "serviceurl": "https://smba.test.com/",
            "aud": "123",
            "iss": "test",
        }
        # Use a simple symmetric key for testing with HS256
        str_token = build_token(token_payload)

        token = JsonWebToken(str_token)

        assert token is not None
        assert token.audience == "123"
        assert token.issuer == "test"
        assert token.key_id == "456"
        assert token.app_id == "test"
        assert token.tenant_id == "789"
        assert token.version is None
        assert token.from_ == "bot"
        assert token.from_id == f"{CallerIds.BOT}:test"
        assert token.service_url == "https://smba.test.com"
        assert str(token) == str_token

    def test_should_be_from_azure(self):
        """Test JWT token identified as azure caller."""
        token_payload = {
            "serviceurl": "https://smba.test.com",
        }
        str_token = build_token(token_payload)

        token = JsonWebToken(str_token)

        assert token is not None
        assert token.app_id == ""
        assert token.from_ == "azure"
        assert token.from_id == CallerIds.AZURE
        assert token.service_url == "https://smba.test.com"

    def test_should_have_default_service_url(self):
        """Test JWT token with default service URL."""
        token_payload = {}
        str_token = build_token(token_payload)

        token = JsonWebToken(str_token)

        assert token is not None
        assert token.app_id == ""
        assert token.from_ == "azure"
        assert token.from_id == CallerIds.AZURE
        assert token.service_url == "https://smba.trafficmanager.net/teams"

    def test_expiration_handling(self):
        """Test JWT token expiration handling."""
        import time

        # Create token with future expiration
        future_exp = int(time.time()) + 3600  # 1 hour from now
        token_payload = {"exp": future_exp}
        str_token = build_token(token_payload)

        token = JsonWebToken(str_token)

        assert token.expiration == future_exp * 1000  # Convert to milliseconds
        assert not token.is_expired()

        # Test with past expiration
        past_exp = int(time.time()) - 3600  # 1 hour ago
        token_payload = {"exp": past_exp}
        str_token = build_token(token_payload)

        token = JsonWebToken(str_token)

        assert token.is_expired()

    def test_no_expiration(self):
        """Test JWT token without expiration."""
        token_payload = {}
        str_token = build_token(token_payload)

        token = JsonWebToken(str_token)

        assert token.expiration is None
        assert not token.is_expired()
