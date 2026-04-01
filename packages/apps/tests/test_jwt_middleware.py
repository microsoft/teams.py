"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

# pyright: basic

from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from fastapi import HTTPException
from microsoft_teams.apps.auth.jwt_middleware import create_jwt_validation_middleware


class TestCreateJwtValidationMiddleware:
    """Test suite for create_jwt_validation_middleware."""

    VALIDATED_PATHS = ["/api/messages"]
    APP_ID = "test-app-id"

    @pytest.fixture
    def mock_call_next(self):
        """Create a mock call_next coroutine."""
        mock_response = MagicMock()
        call_next = AsyncMock(return_value=mock_response)
        return call_next

    def _make_request(self, path: str, auth_header: str | None = None, body: dict | None = None) -> MagicMock:
        """Build a mock FastAPI Request with the given path and auth header."""
        mock_request = MagicMock()
        mock_request.url.path = path
        mock_request.headers.get = MagicMock(return_value=auth_header)
        if body is None:
            body = {"serviceUrl": "https://test.service.url", "id": "activity-123"}
        mock_request.json = AsyncMock(return_value=body)
        mock_request.state = MagicMock()
        return mock_request

    @pytest.mark.asyncio
    async def test_path_not_in_validated_paths(self, mock_call_next):
        """Requests whose path is not in the validated paths list bypass auth and call call_next directly."""
        with patch("microsoft_teams.apps.auth.jwt_middleware.TokenValidator") as mock_validator_class:
            mock_validator = AsyncMock()
            mock_validator_class.for_service.return_value = mock_validator

            middleware = create_jwt_validation_middleware(self.APP_ID, self.VALIDATED_PATHS)

            mock_request = self._make_request("/health")
            response = await middleware(mock_request, mock_call_next)

        mock_call_next.assert_awaited_once_with(mock_request)
        assert response is mock_call_next.return_value

    @pytest.mark.asyncio
    async def test_missing_authorization_header(self, mock_call_next):
        """A request to a validated path with no authorization header raises HTTP 401."""
        with patch("microsoft_teams.apps.auth.jwt_middleware.TokenValidator") as mock_validator_class:
            mock_validator = AsyncMock()
            mock_validator_class.for_service.return_value = mock_validator

            middleware = create_jwt_validation_middleware(self.APP_ID, self.VALIDATED_PATHS)

            mock_request = self._make_request("/api/messages", auth_header=None)

            with pytest.raises(HTTPException) as exc_info:
                await middleware(mock_request, mock_call_next)

        assert exc_info.value.status_code == 401
        mock_call_next.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_invalid_authorization_format(self, mock_call_next):
        """An authorization header that does not start with 'Bearer ' raises HTTP 401."""
        with patch("microsoft_teams.apps.auth.jwt_middleware.TokenValidator") as mock_validator_class:
            mock_validator = AsyncMock()
            mock_validator_class.for_service.return_value = mock_validator

            middleware = create_jwt_validation_middleware(self.APP_ID, self.VALIDATED_PATHS)

            mock_request = self._make_request("/api/messages", auth_header="Basic dXNlcjpwYXNz")

            with pytest.raises(HTTPException) as exc_info:
                await middleware(mock_request, mock_call_next)

        assert exc_info.value.status_code == 401
        mock_call_next.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_valid_token_success(self, mock_call_next):
        """A valid Bearer token is validated, stored in request.state, and call_next is called."""
        mock_jwt_token = MagicMock()

        with (
            patch("microsoft_teams.apps.auth.jwt_middleware.TokenValidator") as mock_validator_class,
            patch("microsoft_teams.apps.auth.jwt_middleware.JsonWebToken", return_value=mock_jwt_token) as mock_jwt_cls,
        ):
            mock_validator = AsyncMock()
            mock_validator_class.for_service.return_value = mock_validator
            mock_validator.validate_token = AsyncMock(return_value=None)

            middleware = create_jwt_validation_middleware(self.APP_ID, self.VALIDATED_PATHS)

            mock_request = self._make_request("/api/messages", auth_header="Bearer my.jwt.token")
            response = await middleware(mock_request, mock_call_next)

        # validate_token was called with the raw token and service URL from the body
        mock_validator.validate_token.assert_awaited_once_with("my.jwt.token", "https://test.service.url")

        # JsonWebToken was constructed with the raw token
        mock_jwt_cls.assert_called_once_with(value="my.jwt.token")

        # The validated token is stored in request state
        assert mock_request.state.validated_token is mock_jwt_token

        # call_next was invoked and its response was returned
        mock_call_next.assert_awaited_once_with(mock_request)
        assert response is mock_call_next.return_value

    @pytest.mark.asyncio
    async def test_jwt_invalid_token_error(self, mock_call_next):
        """When the validator raises jwt.InvalidTokenError the middleware raises HTTP 401."""
        with patch("microsoft_teams.apps.auth.jwt_middleware.TokenValidator") as mock_validator_class:
            mock_validator = AsyncMock()
            mock_validator_class.for_service.return_value = mock_validator
            mock_validator.validate_token = AsyncMock(side_effect=jwt.InvalidTokenError("bad token"))

            middleware = create_jwt_validation_middleware(self.APP_ID, self.VALIDATED_PATHS)

            mock_request = self._make_request("/api/messages", auth_header="Bearer bad.jwt.token")

            with pytest.raises(HTTPException) as exc_info:
                await middleware(mock_request, mock_call_next)

        assert exc_info.value.status_code == 401
        mock_call_next.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_unexpected_exception(self, mock_call_next):
        """When the validator raises a generic Exception the middleware raises HTTP 500."""
        with patch("microsoft_teams.apps.auth.jwt_middleware.TokenValidator") as mock_validator_class:
            mock_validator = AsyncMock()
            mock_validator_class.for_service.return_value = mock_validator
            mock_validator.validate_token = AsyncMock(side_effect=RuntimeError("network error"))

            middleware = create_jwt_validation_middleware(self.APP_ID, self.VALIDATED_PATHS)

            mock_request = self._make_request("/api/messages", auth_header="Bearer some.jwt.token")

            with pytest.raises(HTTPException) as exc_info:
                await middleware(mock_request, mock_call_next)

        assert exc_info.value.status_code == 500
        mock_call_next.assert_not_awaited()
