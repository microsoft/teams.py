"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
from httpx import HTTPStatusError, Request, Response
from microsoft.teams.api import (
    ExchangeUserTokenParams,
    GetUserTokenParams,
    InvokeResponse,
    SignInTokenExchangeInvokeActivity,
    SignInVerifyStateInvokeActivity,
    TokenExchangeInvokeResponse,
)
from microsoft.teams.api.models import (
    Account,
    ConversationAccount,
    SignInExchangeToken,
    SignInStateVerifyQuery,
    TokenResponse,
)
from microsoft.teams.apps.app_oauth import OauthHandlers
from microsoft.teams.apps.events import ErrorEvent, SignInEvent
from microsoft.teams.apps.routing import ActivityContext
from microsoft.teams.common import EventEmitter

# pyright: basic


class TestOauthHandlers:
    """Test cases for OauthHandlers class."""

    @pytest.fixture
    def mock_event_emitter(self):
        """Create a mock event emitter."""
        return MagicMock(spec=EventEmitter)

    @pytest.fixture
    def oauth_handlers(self, mock_event_emitter):
        """Create OauthHandlers instance."""
        return OauthHandlers("test-connection", mock_event_emitter)

    @pytest.fixture
    def mock_context(self):
        """Create a mock ActivityContext."""
        context = MagicMock(spec=ActivityContext)
        context.logger = MagicMock()
        context.api = MagicMock()
        context.api.users.token.exchange = AsyncMock()
        context.api.users.token.get = AsyncMock()
        context.next = AsyncMock()
        return context

    @pytest.fixture
    def token_exchange_activity(self):
        """Create a SignInTokenExchangeInvokeActivity."""
        from_account = Account(id="user-123", name="Test User", role="user")
        recipient = Account(id="bot-456", name="Test Bot", role="bot")
        conversation = ConversationAccount(id="conv-456", conversation_type="personal")

        exchange_token = SignInExchangeToken(id="exchange-id", connection_name="test-connection", token="test-token")

        activity = SignInTokenExchangeInvokeActivity(
            type="invoke",
            id="activity-789",
            from_=from_account,
            recipient=recipient,
            conversation=conversation,
            channel_id="msteams",
            name="signin/tokenExchange",
            value=exchange_token,
        )
        return activity

    @pytest.fixture
    def verify_state_activity(self):
        """Create a SignInVerifyStateInvokeActivity."""
        from_account = Account(id="user-123", name="Test User", role="user")
        recipient = Account(id="bot-456", name="Test Bot", role="bot")
        conversation = ConversationAccount(id="conv-456", conversation_type="personal")

        verify_query = SignInStateVerifyQuery(state="verify-state")

        activity = SignInVerifyStateInvokeActivity(
            type="invoke",
            id="activity-789",
            from_=from_account,
            recipient=recipient,
            conversation=conversation,
            channel_id="msteams",
            name="signin/verifyState",
            value=verify_query,
        )
        return activity

    @pytest.fixture
    def mock_token_response(self):
        """Create a mock token response."""
        return TokenResponse(connection_name="test-connection", token="access-token", expiration="2024-12-31T23:59:59Z")

    @pytest.mark.asyncio
    async def test_sign_in_token_exchange_success(
        self, oauth_handlers, mock_context, token_exchange_activity, mock_token_response
    ):
        """Test successful token exchange."""
        mock_context.activity = token_exchange_activity
        mock_context.api.users.token.exchange.return_value = mock_token_response

        result = await oauth_handlers.sign_in_token_exchange(mock_context)

        # Verify API call
        mock_context.api.users.token.exchange.assert_called_once()
        call_args = mock_context.api.users.token.exchange.call_args[0][0]
        assert isinstance(call_args, ExchangeUserTokenParams)
        assert call_args.connection_name == "test-connection"
        assert call_args.user_id == "user-123"
        assert call_args.channel_id == "msteams"
        assert call_args.exchange_request.token == "test-token"

        # Verify event emission
        oauth_handlers.event_emitter.emit.assert_called_once_with(
            "sign_in", SignInEvent(activity_ctx=mock_context, token_response=mock_token_response)
        )

        # Verify response
        assert result is None

        # Verify next handler called
        mock_context.next.assert_called_once()

    @pytest.mark.asyncio
    async def test_sign_in_token_exchange_connection_name_warning(
        self, oauth_handlers, mock_context, token_exchange_activity, mock_token_response
    ):
        """Test token exchange with different connection name logs warning."""
        token_exchange_activity.value.connection_name = "different-connection"
        mock_context.activity = token_exchange_activity
        mock_context.api.users.token.exchange.return_value = mock_token_response

        await oauth_handlers.sign_in_token_exchange(mock_context)

        # Verify warning was logged
        mock_context.logger.warning.assert_called_once()
        warning_msg = mock_context.logger.warning.call_args[0][0]
        assert "different-connection" in warning_msg
        assert "test-connection" in warning_msg

    @pytest.mark.asyncio
    async def test_sign_in_token_exchange_http_error_404(self, oauth_handlers, mock_context, token_exchange_activity):
        """Test token exchange with HTTP 404 error."""
        mock_context.activity = token_exchange_activity

        # Create mock HTTP error
        mock_request = Mock(spec=Request)
        mock_response = Mock(spec=Response)
        mock_response.status_code = 404
        http_error = HTTPStatusError("Not found", request=mock_request, response=mock_response)

        mock_context.api.users.token.exchange.side_effect = http_error

        result = await oauth_handlers.sign_in_token_exchange(mock_context)

        # Verify no error event emitted for 404
        oauth_handlers.event_emitter.emit.assert_not_called()

        # Verify warning logged
        mock_context.logger.warning.assert_called_once()

        # Verify failure response
        assert isinstance(result, InvokeResponse) and isinstance(result.body, TokenExchangeInvokeResponse)
        assert result.status == 412
        assert result.body.connection_name == "test-connection"
        assert result.body.failure_detail == "Not found"

    @pytest.mark.asyncio
    async def test_sign_in_token_exchange_http_error_500(self, oauth_handlers, mock_context, token_exchange_activity):
        """Test token exchange with HTTP 500 error."""
        mock_context.activity = token_exchange_activity

        # Create mock HTTP error
        mock_request = Mock(spec=Request)
        mock_response = Mock(spec=Response)
        mock_response.status_code = 500
        http_error = HTTPStatusError("Server error", request=mock_request, response=mock_response)

        mock_context.api.users.token.exchange.side_effect = http_error

        result = await oauth_handlers.sign_in_token_exchange(mock_context)

        # Verify error event emitted for 500
        oauth_handlers.event_emitter.emit.assert_called_once_with(
            "error", ErrorEvent(error=http_error, context={"activity": token_exchange_activity})
        )

        # Verify error logged
        mock_context.logger.error.assert_called_once()

        # Verify error response
        assert isinstance(result, InvokeResponse)
        assert result.status == 500

    @pytest.mark.asyncio
    async def test_sign_in_token_exchange_generic_exception(
        self, oauth_handlers, mock_context, token_exchange_activity
    ):
        """Test token exchange with generic exception."""
        mock_context.activity = token_exchange_activity
        generic_error = ValueError("Generic error")
        mock_context.api.users.token.exchange.side_effect = generic_error

        result = await oauth_handlers.sign_in_token_exchange(mock_context)

        # Verify warning logged
        mock_context.logger.warning.assert_called_once()

        # Verify failure response
        assert isinstance(result, InvokeResponse) and isinstance(result.body, TokenExchangeInvokeResponse)
        assert result.status == 412
        assert result.body.failure_detail == "Generic error"

    @pytest.mark.asyncio
    async def test_sign_in_verify_state_success(
        self, oauth_handlers, mock_context, verify_state_activity, mock_token_response
    ):
        """Test successful state verification."""
        mock_context.activity = verify_state_activity
        mock_context.api.users.token.get.return_value = mock_token_response

        result = await oauth_handlers.sign_in_verify_state(mock_context)

        # Verify API call
        mock_context.api.users.token.get.assert_called_once()
        call_args = mock_context.api.users.token.get.call_args[0][0]
        assert isinstance(call_args, GetUserTokenParams)
        assert call_args.connection_name == "test-connection"
        assert call_args.user_id == "user-123"
        assert call_args.channel_id == "msteams"
        assert call_args.code == "verify-state"

        # Verify event emission
        oauth_handlers.event_emitter.emit.assert_called_once_with(
            "sign_in", SignInEvent(activity_ctx=mock_context, token_response=mock_token_response)
        )

        # Verify debug logs
        assert mock_context.logger.debug.call_count == 2

        # Verify response
        assert result is None

        # Verify next handler called
        mock_context.next.assert_called_once()

    @pytest.mark.asyncio
    async def test_sign_in_verify_state_no_state(self, oauth_handlers, mock_context, verify_state_activity):
        """Test state verification with no state."""
        verify_state_activity.value.state = None
        mock_context.activity = verify_state_activity

        result = await oauth_handlers.sign_in_verify_state(mock_context)

        # Verify warning logged
        mock_context.logger.warning.assert_called_once()
        warning_msg = mock_context.logger.warning.call_args[0][0]
        assert "Auth state not present" in warning_msg

        # Verify no API call
        mock_context.api.users.token.get.assert_not_called()

        # Verify 404 response
        assert isinstance(result, InvokeResponse) and result.body is None
        assert result.status == 404

        # Verify next handler still called
        mock_context.next.assert_called_once()

    @pytest.mark.asyncio
    async def test_sign_in_verify_state_http_error_500(self, oauth_handlers, mock_context, verify_state_activity):
        """Test state verification with HTTP 500 error."""
        mock_context.activity = verify_state_activity

        # Create mock HTTP error
        mock_request = Mock(spec=Request)
        mock_response = Mock(spec=Response)
        mock_response.status_code = 500
        http_error = HTTPStatusError("Server error", request=mock_request, response=mock_response)

        mock_context.api.users.token.get.side_effect = http_error

        result = await oauth_handlers.sign_in_verify_state(mock_context)

        # Verify error event emitted
        oauth_handlers.event_emitter.emit.assert_called_once_with(
            "error", ErrorEvent(error=http_error, context={"activity": verify_state_activity})
        )

        # Verify error logged
        mock_context.logger.error.assert_called_once()

        # Verify error response
        assert isinstance(result, InvokeResponse) and result.body is None
        assert result.status == 500

    @pytest.mark.asyncio
    async def test_sign_in_verify_state_http_error_404(self, oauth_handlers, mock_context, verify_state_activity):
        """Test state verification with HTTP 404 error."""
        mock_context.activity = verify_state_activity

        # Create mock HTTP error
        mock_request = Mock(spec=Request)
        mock_response = Mock(spec=Response)
        mock_response.status_code = 404
        http_error = HTTPStatusError("Not found", request=mock_request, response=mock_response)

        mock_context.api.users.token.get.side_effect = http_error

        result = await oauth_handlers.sign_in_verify_state(mock_context)

        # Verify error logged
        mock_context.logger.error.assert_called_once()

        # Verify 412 response
        assert isinstance(result, InvokeResponse) and result.body is None
        assert result.status == 412

    @pytest.mark.asyncio
    async def test_sign_in_verify_state_generic_exception(self, oauth_handlers, mock_context, verify_state_activity):
        """Test state verification with generic exception."""
        mock_context.activity = verify_state_activity
        generic_error = ValueError("Generic error")
        mock_context.api.users.token.get.side_effect = generic_error

        result = await oauth_handlers.sign_in_verify_state(mock_context)

        # Verify error logged
        mock_context.logger.error.assert_called_once()

        # Verify 412 response
        assert isinstance(result, InvokeResponse) and result.body is None
        assert result.status == 412

    def test_oauth_handlers_initialization(self, mock_event_emitter):
        """Test OauthHandlers initialization."""
        handlers = OauthHandlers("my-connection", mock_event_emitter)

        assert handlers.default_connection_name == "my-connection"
        assert handlers.event_emitter == mock_event_emitter
