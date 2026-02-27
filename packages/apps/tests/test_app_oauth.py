"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
from httpx import HTTPStatusError, Request, Response
from microsoft_teams.api import (
    ExchangeUserTokenParams,
    GetUserTokenParams,
    InvokeResponse,
    SignInFailureInvokeActivity,
    SignInTokenExchangeInvokeActivity,
    SignInVerifyStateInvokeActivity,
    TokenExchangeInvokeResponse,
)
from microsoft_teams.api.models import (
    Account,
    ConversationAccount,
    SignInExchangeToken,
    SignInFailure,
    SignInStateVerifyQuery,
    TokenResponse,
)
from microsoft_teams.apps.app_oauth import OauthHandlers
from microsoft_teams.apps.events import ErrorEvent, SignInEvent
from microsoft_teams.apps.routing import ActivityContext
from microsoft_teams.common import EventEmitter

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

    @pytest.fixture
    def failure_activity(self):
        """Create a SignInFailureInvokeActivity."""
        from_account = Account(id="user-123", name="Test User", role="user")
        recipient = Account(id="bot-456", name="Test Bot", role="bot")
        conversation = ConversationAccount(id="conv-456", conversation_type="personal")

        failure = SignInFailure(code="resourcematchfailed", message="Resource match failed")

        activity = SignInFailureInvokeActivity(
            type="invoke",
            id="activity-789",
            from_=from_account,
            recipient=recipient,
            conversation=conversation,
            channel_id="msteams",
            name="signin/failure",
            value=failure,
        )
        return activity

    @pytest.mark.asyncio
    async def test_sign_in_failure_logs_warning(self, oauth_handlers, mock_context, failure_activity):
        """Test that sign_in_failure logs a warning with failure details."""
        mock_context.activity = failure_activity

        await oauth_handlers.sign_in_failure(mock_context)

        # Verify warning logged with failure code and message
        mock_context.logger.warning.assert_called_once()
        warning_msg = mock_context.logger.warning.call_args[0][0]
        assert "resourcematchfailed" in warning_msg
        assert "Resource match failed" in warning_msg
        assert "user-123" in warning_msg
        assert "conv-456" in warning_msg
        assert "Expose an API" in warning_msg

    @pytest.mark.asyncio
    async def test_sign_in_failure_emits_error_event(self, oauth_handlers, mock_context, failure_activity):
        """Test that sign_in_failure emits an error event."""
        mock_context.activity = failure_activity

        await oauth_handlers.sign_in_failure(mock_context)

        # Verify error event emitted
        oauth_handlers.event_emitter.emit.assert_called_once()
        call_args = oauth_handlers.event_emitter.emit.call_args
        assert call_args[0][0] == "error"
        error_event = call_args[0][1]
        assert isinstance(error_event, ErrorEvent)
        assert "resourcematchfailed" in str(error_event.error)
        assert error_event.context["activity"] == failure_activity

    @pytest.mark.asyncio
    async def test_sign_in_failure_returns_200(self, oauth_handlers, mock_context, failure_activity):
        """Test that sign_in_failure returns 200 status."""
        mock_context.activity = failure_activity

        result = await oauth_handlers.sign_in_failure(mock_context)

        assert isinstance(result, InvokeResponse)
        assert result.status == 200

    @pytest.mark.asyncio
    async def test_sign_in_failure_calls_next(self, oauth_handlers, mock_context, failure_activity):
        """Test that sign_in_failure calls next handler."""
        mock_context.activity = failure_activity

        await oauth_handlers.sign_in_failure(mock_context)

        mock_context.next.assert_called_once()

    def test_oauth_handlers_initialization(self, mock_event_emitter):
        """Test OauthHandlers initialization."""
        handlers = OauthHandlers("my-connection", mock_event_emitter)

        assert handlers.default_connection_name == "my-connection"
        assert handlers.event_emitter == mock_event_emitter


@pytest.mark.unit
class TestSignInFailureMiddlewareChain:
    """Integration tests: signin/failure through real routing + middleware chain.

    These tests use the real ActivityRouter and execute_middleware_chain
    to verify that developer-registered handlers actually fire in
    practice — not just in isolation.
    """

    @pytest.fixture
    def failure_activity(self):
        """Create a SignInFailureInvokeActivity."""
        from_account = Account(id="user-123", name="Test User", role="user")
        recipient = Account(id="bot-456", name="Test Bot", role="bot")
        conversation = ConversationAccount(id="conv-456", conversation_type="personal")
        failure = SignInFailure(code="resourcematchfailed", message="Resource match failed")
        return SignInFailureInvokeActivity(
            type="invoke",
            id="activity-789",
            from_=from_account,
            recipient=recipient,
            conversation=conversation,
            channel_id="msteams",
            name="signin/failure",
            value=failure,
        )

    @pytest.fixture
    def router(self):
        """Create a real ActivityRouter."""
        from microsoft_teams.apps.routing.router import ActivityRouter

        return ActivityRouter()

    @pytest.fixture
    def processor(self, router):
        """Create an ActivityProcessor for middleware chain execution."""
        from microsoft_teams.apps.app_process import ActivityProcessor
        from microsoft_teams.common import LocalStorage

        return ActivityProcessor(
            router=router,
            logger=MagicMock(),
            id="bot-456",
            storage=LocalStorage(),
            default_connection_name="graph",
            http_client=MagicMock(),
            token_manager=MagicMock(),
            api_client_settings=None,
        )

    @staticmethod
    def _make_ctx(activity):
        """Build a minimal ActivityContext for chain execution."""
        return ActivityContext(
            activity=activity,
            app_id="bot-456",
            logger=MagicMock(),
            storage=MagicMock(),
            api=MagicMock(),
            user_token=None,
            conversation_ref=MagicMock(),
            is_signed_in=False,
            connection_name="graph",
            sender=MagicMock(),
            app_token=MagicMock(),
        )

    @pytest.mark.asyncio
    async def test_system_default_handler_fires_alone(self, router, processor, failure_activity):
        """System default fires when no developer handler is registered."""
        from microsoft_teams.apps.routing.activity_route_configs import ACTIVITY_ROUTES

        called = []

        async def system_handler(ctx):
            called.append("system")
            await ctx.next()
            return InvokeResponse(status=200)

        config = ACTIVITY_ROUTES["signin.failure"]
        router.add_handler(config.selector, system_handler)

        handlers = router.select_handlers(failure_activity)
        ctx = self._make_ctx(failure_activity)
        result = await processor.execute_middleware_chain(ctx, handlers)

        assert called == ["system"]
        assert result is not None and result.status == 200

    @pytest.mark.asyncio
    async def test_developer_handler_fires_with_system_handler(self, router, processor, failure_activity):
        """Developer on_signin_failure handler fires alongside the system default."""
        from microsoft_teams.apps.routing.activity_route_configs import ACTIVITY_ROUTES

        called = []

        async def system_handler(ctx):
            called.append("system")
            await ctx.next()
            return InvokeResponse(status=200)

        async def developer_handler(ctx):
            called.append("developer")
            await ctx.next()

        config = ACTIVITY_ROUTES["signin.failure"]
        router.add_handler(config.selector, system_handler)
        router.add_handler(config.selector, developer_handler)

        handlers = router.select_handlers(failure_activity)
        ctx = self._make_ctx(failure_activity)
        result = await processor.execute_middleware_chain(ctx, handlers)

        assert called == ["system", "developer"]
        assert result is not None and result.status == 200

    @pytest.mark.asyncio
    async def test_catchall_on_invoke_without_next_blocks_developer_handler(self, router, processor, failure_activity):
        """A catch-all on_invoke that omits ctx.next() blocks later handlers."""
        from microsoft_teams.apps.routing.activity_route_configs import ACTIVITY_ROUTES

        called = []

        async def system_handler(ctx):
            called.append("system")
            await ctx.next()
            return InvokeResponse(status=200)

        async def catchall_invoke(ctx):
            called.append("catchall")
            # Intentionally does NOT call ctx.next()

        async def developer_handler(ctx):
            called.append("developer")
            await ctx.next()

        config_failure = ACTIVITY_ROUTES["signin.failure"]
        config_invoke = ACTIVITY_ROUTES["invoke"]
        router.add_handler(config_failure.selector, system_handler)
        router.add_handler(config_invoke.selector, catchall_invoke)
        router.add_handler(config_failure.selector, developer_handler)

        handlers = router.select_handlers(failure_activity)
        ctx = self._make_ctx(failure_activity)
        await processor.execute_middleware_chain(ctx, handlers)

        assert called == ["system", "catchall"]
        assert "developer" not in called

    @pytest.mark.asyncio
    async def test_catchall_on_invoke_with_next_allows_developer_handler(self, router, processor, failure_activity):
        """A catch-all on_invoke that calls ctx.next() allows later handlers to fire."""
        from microsoft_teams.apps.routing.activity_route_configs import ACTIVITY_ROUTES

        called = []

        async def system_handler(ctx):
            called.append("system")
            await ctx.next()
            return InvokeResponse(status=200)

        async def catchall_invoke(ctx):
            called.append("catchall")
            await ctx.next()  # Properly continues the chain

        async def developer_handler(ctx):
            called.append("developer")
            await ctx.next()

        config_failure = ACTIVITY_ROUTES["signin.failure"]
        config_invoke = ACTIVITY_ROUTES["invoke"]
        router.add_handler(config_failure.selector, system_handler)
        router.add_handler(config_invoke.selector, catchall_invoke)
        router.add_handler(config_failure.selector, developer_handler)

        handlers = router.select_handlers(failure_activity)
        ctx = self._make_ctx(failure_activity)
        result = await processor.execute_middleware_chain(ctx, handlers)

        assert called == ["system", "catchall", "developer"]
        assert result is not None and result.status == 200

    @pytest.mark.asyncio
    async def test_developer_handler_return_value_does_not_override_system(self, router, processor, failure_activity):
        """The first handler's return value wins (system handler returns first on unwind)."""
        from microsoft_teams.apps.routing.activity_route_configs import ACTIVITY_ROUTES

        config = ACTIVITY_ROUTES["signin.failure"]

        async def system_handler(ctx):
            await ctx.next()
            return InvokeResponse(status=200)

        async def developer_handler(ctx):
            await ctx.next()
            return InvokeResponse(status=299)

        router.add_handler(config.selector, system_handler)
        router.add_handler(config.selector, developer_handler)

        handlers = router.select_handlers(failure_activity)
        ctx = self._make_ctx(failure_activity)
        result = await processor.execute_middleware_chain(ctx, handlers)

        assert result is not None
        # The outer handler (system, index 0) calls next() which runs the inner
        # handler (developer, index 1). Inner returns 299 first, then outer
        # returns 200 on unwind — the last non-None return overwrites, so the
        # outer handler's return value wins.
        assert result.status == 200
