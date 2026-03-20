"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

# pyright: basic

from unittest.mock import AsyncMock

import pytest
from microsoft_teams.apps.auth.remote_function_jwt_middleware import (
    validate_remote_function_request,
)
from microsoft_teams.apps.contexts import ClientContext


class TestValidateRemoteFunctionRequest:
    """Tests for validate_remote_function_request."""

    def _base_headers(self) -> dict[str, str]:
        """Return a complete, valid set of request headers."""
        return {
            "Authorization": "Bearer test.jwt.token",
            "X-Teams-App-Session-Id": "session-123",
            "X-Teams-Page-Id": "page-456",
        }

    def _make_validator(self, payload: dict | None = None) -> AsyncMock:
        """Return a mock TokenValidator whose validate_token returns *payload*."""
        if payload is None:
            payload = {"oid": "user-123", "tid": "tenant-456", "name": "Test User"}
        mock_validator = AsyncMock()
        mock_validator.validate_token = AsyncMock(return_value=payload)
        return mock_validator

    @pytest.mark.asyncio
    async def test_validate_request_missing_header(self):
        """When a required header is missing the function returns (None, error_message)."""
        headers = {
            # Missing Authorization and X-Teams-App-Session-Id
            "X-Teams-Page-Id": "page-456",
        }
        context, error = await validate_remote_function_request(headers, self._make_validator())

        assert context is None
        assert error is not None
        assert len(error) > 0

    @pytest.mark.asyncio
    async def test_validate_request_no_token_validator(self):
        """When entra_token_validator is None the function returns (None, 'Token validator not configured')."""
        headers = self._base_headers()
        context, error = await validate_remote_function_request(headers, None)

        assert context is None
        assert error == "Token validator not configured"

    @pytest.mark.asyncio
    async def test_validate_request_valid(self):
        """All valid inputs → returns (ClientContext, None) with correct field values."""
        headers = self._base_headers()
        validator = self._make_validator()

        context, error = await validate_remote_function_request(headers, validator)

        assert error is None
        assert isinstance(context, ClientContext)
        assert context.user_id == "user-123"
        assert context.tenant_id == "tenant-456"
        assert context.user_name == "Test User"
        assert context.app_session_id == "session-123"
        assert context.page_id == "page-456"
        assert context.auth_token == "test.jwt.token"

        validator.validate_token.assert_awaited_once_with("test.jwt.token")

    @pytest.mark.asyncio
    async def test_validate_request_missing_token_fields(self):
        """When the token payload is missing oid/tid/name the function returns (None, error_message)."""
        headers = self._base_headers()
        # Payload deliberately omits required fields
        validator = self._make_validator(payload={"scp": "user.read"})

        context, error = await validate_remote_function_request(headers, validator)

        assert context is None
        assert error is not None
        # All three missing fields should be named in the message
        assert "oid" in error
        assert "tid" in error
        assert "name" in error

    @pytest.mark.asyncio
    async def test_validate_request_case_insensitive_headers(self):
        """Lowercase header names are treated the same as the canonical casing."""
        headers = {
            "authorization": "Bearer test.jwt.token",
            "x-teams-app-session-id": "session-123",
            "x-teams-page-id": "page-456",
        }
        validator = self._make_validator()

        context, error = await validate_remote_function_request(headers, validator)

        assert error is None
        assert isinstance(context, ClientContext)
        assert context.app_session_id == "session-123"
        assert context.page_id == "page-456"
        assert context.auth_token == "test.jwt.token"
