"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import logging
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator
from unittest.mock import AsyncMock, MagicMock, Mock, patch

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
from microsoft_teams.api.auth.cloud_environment import PUBLIC
from microsoft_teams.api.models import (
    Account,
    ConversationAccount,
    SignInExchangeToken,
    SignInFailure,
    SignInStateVerifyQuery,
    TokenResponse,
)
from microsoft_teams.apps.app_oauth import OauthHandlers
from microsoft_teams.apps.app_process import ActivityProcessor
from microsoft_teams.apps.events import ErrorEvent, SignInEvent, SignInFailureEvent
from microsoft_teams.apps.oauth_flow import OAuthFlow, OAuthFlowRegistry
from microsoft_teams.apps.routing import ActivityContext
from microsoft_teams.apps.routing.activity_route_configs import ACTIVITY_ROUTES
from microsoft_teams.apps.routing.router import ActivityRouter
from microsoft_teams.apps.state import TurnState, TurnStateContainer
from microsoft_teams.apps.token_provider import AppTokenProvider
from microsoft_teams.common import EventEmitter, LocalStorage

# pyright: basic


class RecordingSpan:
    def __init__(self, name: str, options: dict[str, Any]):
        self.name = name
        self.options = options
        self.attributes: dict[str, Any] = {}

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value


class RecordingTracer:
    def __init__(self):
        self.spans: list[RecordingSpan] = []

    @contextmanager
    def start_as_current_span(self, name: str, **kwargs: Any) -> Iterator[RecordingSpan]:
        span = RecordingSpan(name, kwargs)
        self.spans.append(span)
        yield span


def create_turn_state(user_data: dict[str, Any] | None = None) -> TurnStateContainer:
    return TurnStateContainer(
        conversation=TurnState(),
        conversation_id="conv-456",
        user=TurnState(user_data),
        user_id="user-123",
    )


def iso(epoch_seconds: float) -> str:
    return datetime.fromtimestamp(epoch_seconds, tz=timezone.utc).isoformat()


def pending_marker_keys(state: TurnStateContainer) -> set[str]:
    """The reserved pending sign-in keys currently stored in user state."""
    assert state.user is not None
    return {key for key in state.user if key.startswith("__oauth:pending:")}


def create_pending_state(*hints: tuple[str, float, bool]) -> TurnStateContainer:
    user_data: dict[str, Any] = {}
    for connection_name, created_at, sso_offered in hints:
        stamp = iso(created_at)
        user_data[f"__oauth:pending:{connection_name}"] = stamp
        if sso_offered:
            user_data[f"__oauth:pending:sso:{connection_name}"] = stamp
    return create_turn_state(user_data)


def oauth_http_error(status: int, message: str) -> HTTPStatusError:
    request = Request("GET", "https://token.example")
    response = Response(status, request=request)
    return HTTPStatusError(message, request=request, response=response)


class TestOauthHandlers:
    """Test cases for OauthHandlers class."""

    @pytest.fixture
    def mock_event_emitter(self):
        """Create a mock event emitter."""
        return MagicMock(spec=EventEmitter)

    @pytest.fixture
    def oauth_handlers(self, mock_event_emitter):
        """Create OauthHandlers instance."""
        return OauthHandlers("test-connection", mock_event_emitter, OAuthFlowRegistry())

    @pytest.fixture
    def mock_context(self):
        """Create a mock ActivityContext."""
        context = MagicMock(spec=ActivityContext)
        context.logger = MagicMock()
        context.api = MagicMock()
        context.api.users.exchange_token = AsyncMock()
        context.api.users.get_token = AsyncMock()
        context.next = AsyncMock()
        context.state = None
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
        mock_context.api.users.exchange_token.return_value = mock_token_response

        result = await oauth_handlers.sign_in_token_exchange(mock_context)

        # Verify API call
        mock_context.api.users.exchange_token.assert_called_once()
        call_args = mock_context.api.users.exchange_token.call_args[0][0]
        assert isinstance(call_args, ExchangeUserTokenParams)
        assert call_args.connection_name == "test-connection"
        assert call_args.user_id == "user-123"
        assert call_args.channel_id == "msteams"
        assert call_args.exchange_request.token == "test-token"

        # Verify event emission
        oauth_handlers.event_emitter.emit_async.assert_awaited_once_with(
            "sign_in",
            SignInEvent(
                activity_ctx=mock_context,
                token_response=mock_token_response,
                connection_name="test-connection",
            ),
        )

        # Verify the context is marked signed-in with the exchanged token so
        # "sign_in" event handlers can immediately use ctx.user_token / ctx.user_graph.
        assert mock_context.is_signed_in is True
        assert mock_context.user_token == "access-token"

        # Verify response
        assert result is None

        # Verify next handler called
        mock_context.next.assert_called_once()

    @pytest.mark.asyncio
    async def test_sign_in_token_exchange_records_success_telemetry(
        self, oauth_handlers, mock_context, token_exchange_activity, mock_token_response
    ):
        mock_context.activity = token_exchange_activity
        mock_context.api.users.exchange_token.return_value = mock_token_response
        tracer = RecordingTracer()

        with (
            pytest.MonkeyPatch.context() as monkeypatch,
        ):
            operation_calls = []
            monkeypatch.setattr("microsoft_teams.apps.app_oauth.get_tracer", lambda: tracer)
            monkeypatch.setattr(
                "microsoft_teams.apps.app_oauth.record_oauth_operation",
                lambda *args: operation_calls.append(args),
            )

            await oauth_handlers.sign_in_token_exchange(mock_context)

        assert tracer.spans[0].name == "microsoft.teams.oauth.token_exchange"
        assert tracer.spans[0].options == {"record_exception": False, "set_status_on_exception": False}
        assert tracer.spans[0].attributes == {
            "oauth.connection": "test-connection",
            "oauth.operation": "token_exchange",
            "oauth.callback.invoked": True,
            "oauth.result": "success",
        }
        assert operation_calls[0][:3] == ("test-connection", "token_exchange", "success")
        assert operation_calls[0][3] >= 0
        assert "test-token" not in tracer.spans[0].attributes.values()
        assert "access-token" not in tracer.spans[0].attributes.values()

    @pytest.mark.asyncio
    async def test_sign_in_token_exchange_connection_name_warning(
        self, oauth_handlers, mock_context, token_exchange_activity, mock_token_response, caplog
    ):
        """Test token exchange with different connection name."""
        token_exchange_activity.value.connection_name = "different-connection"
        mock_context.activity = token_exchange_activity
        mock_context.api.users.exchange_token.return_value = mock_token_response

        with caplog.at_level(logging.WARNING, logger="microsoft_teams.apps.app_oauth"):
            await oauth_handlers.sign_in_token_exchange(mock_context)

        mock_context.api.users.exchange_token.assert_called_once()
        assert "nor a registered OAuth flow" in caplog.text

    @pytest.mark.asyncio
    async def test_sign_in_token_exchange_registered_connection_does_not_warn(
        self, oauth_handlers, mock_context, token_exchange_activity, mock_token_response, caplog
    ):
        token_exchange_activity.value.connection_name = "different-connection"
        oauth_handlers.oauth_registry.add(OAuthFlow("Different-Connection"))
        mock_context.activity = token_exchange_activity
        mock_context.api.users.exchange_token.return_value = mock_token_response

        with caplog.at_level(logging.WARNING, logger="microsoft_teams.apps.app_oauth"):
            await oauth_handlers.sign_in_token_exchange(mock_context)

        mock_context.api.users.exchange_token.assert_called_once()
        assert "Token verification will likely fail" not in caplog.text

    @pytest.mark.asyncio
    async def test_sign_in_token_exchange_http_error_404(self, oauth_handlers, mock_context, token_exchange_activity):
        """Test token exchange with HTTP 404 error."""
        mock_context.activity = token_exchange_activity

        # Create mock HTTP error
        mock_request = Mock(spec=Request)
        mock_response = Mock(spec=Response)
        mock_response.status_code = 404
        http_error = HTTPStatusError("Not found", request=mock_request, response=mock_response)

        mock_context.api.users.exchange_token.side_effect = http_error

        result = await oauth_handlers.sign_in_token_exchange(mock_context)

        # Verify no error event emitted for 404
        oauth_handlers.event_emitter.emit_async.assert_not_awaited()

        # Verify failure response
        assert isinstance(result, InvokeResponse) and isinstance(result.body, TokenExchangeInvokeResponse)
        assert result.status == 412
        assert result.body.connection_name == "test-connection"
        assert result.body.failure_detail == "Not found"

    @pytest.mark.asyncio
    async def test_sign_in_token_exchange_expected_http_error_records_failure_without_oauth_error(
        self, oauth_handlers, mock_context, token_exchange_activity
    ):
        mock_context.activity = token_exchange_activity
        mock_request = Mock(spec=Request)
        mock_response = Mock(spec=Response)
        mock_response.status_code = 404
        http_error = HTTPStatusError("Not found", request=mock_request, response=mock_response)
        mock_context.api.users.exchange_token.side_effect = http_error
        tracer = RecordingTracer()

        with (
            pytest.MonkeyPatch.context() as monkeypatch,
        ):
            operation_calls = []
            error_calls = []
            monkeypatch.setattr("microsoft_teams.apps.app_oauth.get_tracer", lambda: tracer)
            monkeypatch.setattr(
                "microsoft_teams.apps.app_oauth.record_oauth_operation",
                lambda *args: operation_calls.append(args),
            )
            monkeypatch.setattr(
                "microsoft_teams.apps.app_oauth.record_oauth_error",
                lambda *args: error_calls.append(args),
            )

            await oauth_handlers.sign_in_token_exchange(mock_context)

        assert tracer.spans[0].attributes == {
            "oauth.connection": "test-connection",
            "oauth.operation": "token_exchange",
            "invoke.response.status": 412,
            "oauth.result": "failure",
        }
        assert operation_calls[0][:3] == ("test-connection", "token_exchange", "failure")
        assert error_calls == []

    @pytest.mark.asyncio
    async def test_sign_in_token_exchange_http_error_500(self, oauth_handlers, mock_context, token_exchange_activity):
        """Test token exchange with HTTP 500 error."""
        mock_context.activity = token_exchange_activity

        # Create mock HTTP error
        mock_request = Mock(spec=Request)
        mock_response = Mock(spec=Response)
        mock_response.status_code = 500
        http_error = HTTPStatusError("Server error", request=mock_request, response=mock_response)

        mock_context.api.users.exchange_token.side_effect = http_error

        result = await oauth_handlers.sign_in_token_exchange(mock_context)

        # Verify error event emitted for 500
        oauth_handlers.event_emitter.emit_async.assert_awaited_once_with(
            "error", ErrorEvent(error=http_error, context={"activity": token_exchange_activity})
        )

        # Verify error response
        assert isinstance(result, InvokeResponse)
        assert result.status == 500

    @pytest.mark.asyncio
    async def test_sign_in_token_exchange_unexpected_http_error_records_oauth_error(
        self, oauth_handlers, mock_context, token_exchange_activity
    ):
        mock_context.activity = token_exchange_activity
        mock_request = Mock(spec=Request)
        mock_response = Mock(spec=Response)
        mock_response.status_code = 500
        http_error = HTTPStatusError("Server error", request=mock_request, response=mock_response)
        mock_context.api.users.exchange_token.side_effect = http_error
        tracer = RecordingTracer()

        with (
            pytest.MonkeyPatch.context() as monkeypatch,
        ):
            operation_calls = []
            error_calls = []
            record_exception_calls = []
            monkeypatch.setattr("microsoft_teams.apps.app_oauth.get_tracer", lambda: tracer)
            monkeypatch.setattr(
                "microsoft_teams.apps.app_oauth.record_oauth_operation",
                lambda *args: operation_calls.append(args),
            )
            monkeypatch.setattr(
                "microsoft_teams.apps.app_oauth.record_oauth_error",
                lambda *args: error_calls.append(args),
            )
            monkeypatch.setattr(
                "microsoft_teams.apps.app_oauth.record_exception",
                lambda *args: record_exception_calls.append(args),
            )

            await oauth_handlers.sign_in_token_exchange(mock_context)

        assert tracer.spans[0].attributes == {
            "oauth.connection": "test-connection",
            "oauth.operation": "token_exchange",
            "oauth.error.type": "http_error",
            "invoke.response.status": 500,
            "oauth.result": "failure",
        }
        assert operation_calls[0][:3] == ("test-connection", "token_exchange", "failure")
        assert error_calls == [("test-connection", "token_exchange", "http_error")]
        assert record_exception_calls == [(tracer.spans[0], http_error)]

    @pytest.mark.asyncio
    async def test_sign_in_token_exchange_generic_exception(
        self, oauth_handlers, mock_context, token_exchange_activity
    ):
        """A non-HTTP crash propagates instead of being reported as a 412 miss.

        412 tells Teams the exchange merely missed and to offer the sign-in
        button. A transport fault or a bug is not a miss, so it travels up to the
        app's error handling, which emits the ErrorEvent once and re-raises.
        """
        mock_context.activity = token_exchange_activity
        generic_error = ValueError("Generic error")
        mock_context.api.users.exchange_token.side_effect = generic_error

        with pytest.raises(ValueError, match="Generic error"):
            await oauth_handlers.sign_in_token_exchange(mock_context)

        # The app processor owns the ErrorEvent for propagated errors; emitting
        # here too would report the same failure twice.
        oauth_handlers.event_emitter.emit_async.assert_not_awaited()
        # next() still runs, so the middleware chain is not left dangling.
        mock_context.next.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_sign_in_token_exchange_unexpected_exception_records_failure_oauth_error(
        self, oauth_handlers, mock_context, token_exchange_activity
    ):
        mock_context.activity = token_exchange_activity
        generic_error = ValueError("Generic error")
        mock_context.api.users.exchange_token.side_effect = generic_error
        tracer = RecordingTracer()

        with pytest.MonkeyPatch.context() as monkeypatch:
            operation_calls = []
            error_calls = []
            record_exception_calls = []
            monkeypatch.setattr("microsoft_teams.apps.app_oauth.get_tracer", lambda: tracer)
            monkeypatch.setattr(
                "microsoft_teams.apps.app_oauth.record_oauth_operation",
                lambda *args: operation_calls.append(args),
            )
            monkeypatch.setattr(
                "microsoft_teams.apps.app_oauth.record_oauth_error",
                lambda *args: error_calls.append(args),
            )
            monkeypatch.setattr(
                "microsoft_teams.apps.app_oauth.record_exception",
                lambda *args: record_exception_calls.append(args),
            )

            with pytest.raises(ValueError, match="Generic error"):
                await oauth_handlers.sign_in_token_exchange(mock_context)

        # No invoke.response.status: the handler never produced a response.
        assert tracer.spans[0].attributes == {
            "oauth.connection": "test-connection",
            "oauth.operation": "token_exchange",
            "oauth.error.type": "exception",
            "oauth.result": "failure",
        }
        assert operation_calls[0][:3] == ("test-connection", "token_exchange", "failure")
        assert error_calls == [("test-connection", "token_exchange", "exception")]
        assert record_exception_calls == [(tracer.spans[0], generic_error)]

    @pytest.mark.asyncio
    async def test_sign_in_verify_state_success(
        self, oauth_handlers, mock_context, verify_state_activity, mock_token_response
    ):
        """Test successful state verification."""
        mock_context.activity = verify_state_activity
        mock_context.api.users.get_token.return_value = mock_token_response

        result = await oauth_handlers.sign_in_verify_state(mock_context)

        # Verify API call
        mock_context.api.users.get_token.assert_called_once()
        call_args = mock_context.api.users.get_token.call_args[0][0]
        assert isinstance(call_args, GetUserTokenParams)
        assert call_args.connection_name == "test-connection"
        assert call_args.user_id == "user-123"
        assert call_args.channel_id == "msteams"
        assert call_args.code == "verify-state"

        # Verify event emission
        oauth_handlers.event_emitter.emit_async.assert_awaited_once_with(
            "sign_in",
            SignInEvent(
                activity_ctx=mock_context,
                token_response=mock_token_response,
                connection_name="test-connection",
            ),
        )

        # Verify the context is marked signed-in with the verified token so
        # "sign_in" event handlers can immediately use ctx.user_token / ctx.user_graph.
        assert mock_context.is_signed_in is True
        assert mock_context.user_token == "access-token"

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

        # Verify no API call
        mock_context.api.users.get_token.assert_not_called()

        # Verify 404 response
        assert isinstance(result, InvokeResponse) and result.body is None
        assert result.status == 404

        # Verify next handler still called
        mock_context.next.assert_called_once()

    @pytest.mark.asyncio
    async def test_sign_in_verify_state_no_state_records_no_token_without_oauth_error(
        self, oauth_handlers, mock_context, verify_state_activity
    ):
        verify_state_activity.value.state = None
        mock_context.activity = verify_state_activity
        tracer = RecordingTracer()

        with pytest.MonkeyPatch.context() as monkeypatch:
            operation_calls = []
            error_calls = []
            monkeypatch.setattr("microsoft_teams.apps.app_oauth.get_tracer", lambda: tracer)
            monkeypatch.setattr(
                "microsoft_teams.apps.app_oauth.record_oauth_operation",
                lambda *args: operation_calls.append(args),
            )
            monkeypatch.setattr(
                "microsoft_teams.apps.app_oauth.record_oauth_error",
                lambda *args: error_calls.append(args),
            )

            await oauth_handlers.sign_in_verify_state(mock_context)

        assert tracer.spans[0].attributes == {
            "oauth.connection": "test-connection",
            "oauth.operation": "verify_state",
            "invoke.response.status": 404,
            "oauth.result": "no_token",
        }
        assert operation_calls[0][:3] == ("test-connection", "verify_state", "no_token")
        assert error_calls == []

    @pytest.mark.asyncio
    async def test_sign_in_verify_state_http_error_500(self, oauth_handlers, mock_context, verify_state_activity):
        """Test state verification with HTTP 500 error."""
        mock_context.activity = verify_state_activity

        # Create mock HTTP error
        mock_request = Mock(spec=Request)
        mock_response = Mock(spec=Response)
        mock_response.status_code = 500
        http_error = HTTPStatusError("Server error", request=mock_request, response=mock_response)

        mock_context.api.users.get_token.side_effect = http_error

        result = await oauth_handlers.sign_in_verify_state(mock_context)

        # Verify error event emitted
        oauth_handlers.event_emitter.emit_async.assert_awaited_once_with(
            "error", ErrorEvent(error=http_error, context={"activity": verify_state_activity})
        )

        # Verify error response
        assert isinstance(result, InvokeResponse) and result.body is None
        assert result.status == 500

    @pytest.mark.asyncio
    async def test_sign_in_verify_state_unexpected_exception_records_oauth_error(
        self, oauth_handlers, mock_context, verify_state_activity
    ):
        mock_context.activity = verify_state_activity
        generic_error = ValueError("Generic error")
        mock_context.api.users.get_token.side_effect = generic_error
        tracer = RecordingTracer()

        with pytest.MonkeyPatch.context() as monkeypatch:
            operation_calls = []
            error_calls = []
            record_exception_calls = []
            monkeypatch.setattr("microsoft_teams.apps.app_oauth.get_tracer", lambda: tracer)
            monkeypatch.setattr(
                "microsoft_teams.apps.app_oauth.record_oauth_operation",
                lambda *args: operation_calls.append(args),
            )
            monkeypatch.setattr(
                "microsoft_teams.apps.app_oauth.record_oauth_error",
                lambda *args: error_calls.append(args),
            )
            monkeypatch.setattr(
                "microsoft_teams.apps.app_oauth.record_exception",
                lambda *args: record_exception_calls.append(args),
            )

            with pytest.raises(ValueError, match="Generic error"):
                await oauth_handlers.sign_in_verify_state(mock_context)

        # No invoke.response.status: the handler never produced a response.
        assert tracer.spans[0].attributes == {
            "oauth.connection": "test-connection",
            "oauth.operation": "verify_state",
            "oauth.error.type": "exception",
            "oauth.result": "failure",
        }
        assert operation_calls[0][:3] == ("test-connection", "verify_state", "failure")
        assert error_calls == [("test-connection", "verify_state", "exception")]
        assert record_exception_calls == [(tracer.spans[0], generic_error)]

    @pytest.mark.asyncio
    async def test_sign_in_verify_state_expected_http_error_records_failure_without_oauth_error(
        self, oauth_handlers, mock_context, verify_state_activity
    ):
        """An expected miss is not an OAuth error and ends as 404, not 412."""
        mock_context.activity = verify_state_activity
        mock_request = Mock(spec=Request)
        mock_response = Mock(spec=Response)
        mock_response.status_code = 404
        http_error = HTTPStatusError("Not found", request=mock_request, response=mock_response)
        mock_context.api.users.get_token.side_effect = http_error
        tracer = RecordingTracer()

        with pytest.MonkeyPatch.context() as monkeypatch:
            operation_calls = []
            error_calls = []
            monkeypatch.setattr("microsoft_teams.apps.app_oauth.get_tracer", lambda: tracer)
            monkeypatch.setattr(
                "microsoft_teams.apps.app_oauth.record_oauth_operation",
                lambda *args: operation_calls.append(args),
            )
            monkeypatch.setattr(
                "microsoft_teams.apps.app_oauth.record_oauth_error",
                lambda *args: error_calls.append(args),
            )

            await oauth_handlers.sign_in_verify_state(mock_context)

        assert tracer.spans[0].attributes == {
            "oauth.connection": "test-connection",
            "oauth.operation": "verify_state",
            "invoke.response.status": 404,
            "oauth.result": "no_token",
        }
        assert operation_calls[0][:3] == ("test-connection", "verify_state", "no_token")
        assert error_calls == []

    @pytest.mark.asyncio
    @pytest.mark.parametrize("status_code", [400, 404, 412])
    async def test_sign_in_verify_state_expected_miss_statuses_end_as_404(
        self, oauth_handlers, mock_context, verify_state_activity, status_code
    ):
        """400, 404 and 412 are all candidate misses, not terminal failures.

        ``signin/verifyState`` carries no connection name, so the Token Service
        rejecting a code only rules out the connection that was probed. Treating
        400 or 412 as terminal would abandon the remaining candidates.
        """
        mock_context.activity = verify_state_activity
        mock_response = Mock(spec=Response)
        mock_response.status_code = status_code
        mock_context.api.users.get_token.side_effect = HTTPStatusError(
            f"HTTP {status_code}", request=Mock(spec=Request), response=mock_response
        )

        result = await oauth_handlers.sign_in_verify_state(mock_context)

        assert isinstance(result, InvokeResponse) and result.body is None
        assert result.status == 404

    @pytest.mark.asyncio
    async def test_sign_in_verify_state_probes_every_candidate_before_giving_up(
        self, oauth_handlers, mock_context, verify_state_activity, mock_token_response
    ):
        """A miss on one candidate must not stop the probe.

        Red-green: with 400 treated as terminal, the second connection is never
        probed and this returns 404 instead of signing the user in.
        """
        mock_context.activity = verify_state_activity
        flow = oauth_handlers.oauth_registry.add(OAuthFlow("graph"))

        def responses(params):
            if params.connection_name == "graph":
                return mock_token_response
            mock_response = Mock(spec=Response)
            mock_response.status_code = 400
            raise HTTPStatusError("Bad request", request=Mock(spec=Request), response=mock_response)

        mock_context.api.users.get_token.side_effect = responses

        result = await oauth_handlers.sign_in_verify_state(mock_context)

        assert result is None
        probed = [call.args[0].connection_name for call in mock_context.api.users.get_token.await_args_list]
        assert "graph" in probed
        assert flow.connection_name == "graph"

    @pytest.mark.asyncio
    async def test_sign_in_verify_state_unexpected_http_status_stops_immediately(
        self, oauth_handlers, mock_context, verify_state_activity
    ):
        """A 500 is not a miss, so probing stops and the status is preserved."""
        mock_context.activity = verify_state_activity
        oauth_handlers.oauth_registry.add(OAuthFlow("graph"))
        mock_response = Mock(spec=Response)
        mock_response.status_code = 500
        mock_context.api.users.get_token.side_effect = HTTPStatusError(
            "Server error", request=Mock(spec=Request), response=mock_response
        )

        result = await oauth_handlers.sign_in_verify_state(mock_context)

        assert isinstance(result, InvokeResponse)
        assert result.status == 500
        assert mock_context.api.users.get_token.await_count == 1

    @pytest.mark.asyncio
    async def test_sign_in_verify_state_http_error_404(self, oauth_handlers, mock_context, verify_state_activity):
        """A 404 from the only candidate exhausts the probe and returns 404."""
        mock_context.activity = verify_state_activity

        # Create mock HTTP error
        mock_request = Mock(spec=Request)
        mock_response = Mock(spec=Response)
        mock_response.status_code = 404
        http_error = HTTPStatusError("Not found", request=mock_request, response=mock_response)

        mock_context.api.users.get_token.side_effect = http_error

        result = await oauth_handlers.sign_in_verify_state(mock_context)

        assert isinstance(result, InvokeResponse) and result.body is None
        assert result.status == 404

    @pytest.mark.asyncio
    async def test_sign_in_verify_state_generic_exception(self, oauth_handlers, mock_context, verify_state_activity):
        """A non-HTTP crash propagates rather than being flattened into a 412."""
        mock_context.activity = verify_state_activity
        generic_error = ValueError("Generic error")
        mock_context.api.users.get_token.side_effect = generic_error

        with pytest.raises(ValueError, match="Generic error"):
            await oauth_handlers.sign_in_verify_state(mock_context)

    @pytest.mark.asyncio
    async def test_sign_in_verify_state_generic_exception_does_not_double_report(
        self, oauth_handlers, mock_context, verify_state_activity
    ):
        """The propagated crash is reported once, by the app processor.

        ``ActivityProcessor`` already emits an ErrorEvent and re-raises for any
        exception out of a handler, so emitting here as well would surface the
        same failure twice. ``next()`` still runs from the finally block.
        """
        mock_context.activity = verify_state_activity
        mock_context.api.users.get_token.side_effect = ValueError("Generic error")

        with pytest.raises(ValueError, match="Generic error"):
            await oauth_handlers.sign_in_verify_state(mock_context)

        oauth_handlers.event_emitter.emit_async.assert_not_awaited()
        mock_context.next.assert_awaited_once()

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
        """Test that sign_in_failure still emits an error event (kept for backwards compatibility)."""
        mock_context.activity = failure_activity

        await oauth_handlers.sign_in_failure(mock_context)

        error_calls = [c for c in oauth_handlers.event_emitter.emit_async.call_args_list if c[0][0] == "error"]
        assert len(error_calls) == 1
        error_event = error_calls[0][0][1]
        assert isinstance(error_event, ErrorEvent)
        assert "resourcematchfailed" in str(error_event.error)
        assert error_event.context is not None
        assert error_event.context["activity"] == failure_activity

    @pytest.mark.asyncio
    async def test_sign_in_failure_emits_sign_in_failure_event(self, oauth_handlers, mock_context, failure_activity):
        """Test that sign_in_failure additionally emits a structured SignInFailureEvent."""
        mock_context.activity = failure_activity

        await oauth_handlers.sign_in_failure(mock_context)

        failure_calls = [
            c for c in oauth_handlers.event_emitter.emit_async.call_args_list if c[0][0] == "sign_in_failure"
        ]
        assert len(failure_calls) == 1
        event = failure_calls[0][0][1]
        assert isinstance(event, SignInFailureEvent)
        assert event.code == "resourcematchfailed"
        assert event.message == "Resource match failed"
        assert event.connection_name == "test-connection"
        assert event.activity_ctx is mock_context

    @pytest.mark.asyncio
    async def test_sign_in_failure_returns_none(self, oauth_handlers, mock_context, failure_activity):
        """Test that sign_in_failure returns None (process_activity wraps into 200)."""
        mock_context.activity = failure_activity

        result = await oauth_handlers.sign_in_failure(mock_context)

        assert result is None

    @pytest.mark.asyncio
    async def test_sign_in_failure_records_notified_telemetry_without_message(
        self, oauth_handlers, mock_context, failure_activity
    ):
        mock_context.activity = failure_activity
        tracer = RecordingTracer()

        with pytest.MonkeyPatch.context() as monkeypatch:
            operation_calls = []
            monkeypatch.setattr("microsoft_teams.apps.app_oauth.get_tracer", lambda: tracer)
            monkeypatch.setattr(
                "microsoft_teams.apps.app_oauth.record_oauth_operation",
                lambda *args: operation_calls.append(args),
            )

            await oauth_handlers.sign_in_failure(mock_context)

        assert tracer.spans[0].attributes == {
            "oauth.connection": "test-connection",
            "oauth.operation": "signin_failure",
            "oauth.failure.code": "resourcematchfailed",
            "oauth.callback.invoked": True,
            "oauth.result": "notified",
        }
        assert operation_calls[0][:3] == ("test-connection", "signin_failure", "notified")
        assert "Resource match failed" not in tracer.spans[0].attributes.values()

    @pytest.mark.asyncio
    async def test_sign_in_failure_calls_next(self, oauth_handlers, mock_context, failure_activity):
        """Test that sign_in_failure calls next handler."""
        mock_context.activity = failure_activity

        await oauth_handlers.sign_in_failure(mock_context)

        mock_context.next.assert_called_once()

    @pytest.mark.asyncio
    async def test_token_exchange_routes_case_insensitive_explicit_connection_without_state(
        self, oauth_handlers, mock_context, token_exchange_activity, mock_token_response
    ):
        graph = oauth_handlers.oauth_registry.add(OAuthFlow("Graph"))
        github = oauth_handlers.oauth_registry.add(OAuthFlow("GitHub"))
        calls = []

        @graph.on_signin
        async def on_graph(event):
            calls.append(("graph", event.connection_name))

        @github.on_signin
        async def on_github(event):
            calls.append(("github", event.connection_name))

        oauth_handlers.event_emitter.emit_async.side_effect = lambda name, event: calls.append(
            (f"global:{name}", getattr(event, "connection_name", None))
        )
        token_exchange_activity.value.connection_name = "gItHuB"
        mock_context.activity = token_exchange_activity
        mock_context.state = None
        mock_context.api.users.exchange_token.return_value = mock_token_response

        result = await oauth_handlers.sign_in_token_exchange(mock_context)

        assert result is None
        assert calls == [("global:sign_in", "GitHub"), ("github", "GitHub")]
        params = mock_context.api.users.exchange_token.call_args.args[0]
        assert params.connection_name == "gItHuB"

    @pytest.mark.asyncio
    async def test_token_exchange_invokes_global_then_flow_handlers_in_registration_order(
        self, oauth_handlers, mock_context, token_exchange_activity, mock_token_response
    ):
        flow = oauth_handlers.oauth_registry.add(OAuthFlow("test-connection"))
        calls = []
        oauth_handlers.event_emitter.emit_async.side_effect = lambda name, _: calls.append(f"global:{name}")

        @flow.on_signin
        async def first(_):
            calls.append("flow:first")

        @flow.on_signin
        async def second(_):
            calls.append("flow:second")

        mock_context.activity = token_exchange_activity
        mock_context.api.users.exchange_token.return_value = mock_token_response

        await oauth_handlers.sign_in_token_exchange(mock_context)

        assert calls == ["global:sign_in", "flow:first", "flow:second"]

    @pytest.mark.asyncio
    async def test_async_global_handler_completes_before_flow_handler(
        self, mock_context, token_exchange_activity, mock_token_response
    ):
        emitter = EventEmitter()
        registry = OAuthFlowRegistry()
        flow = registry.add(OAuthFlow("test-connection"))
        handlers = OauthHandlers("test-connection", emitter, registry)
        calls = []

        async def global_handler(_):
            await asyncio.sleep(0)
            calls.append("global")

        emitter.on("sign_in", global_handler)

        @flow.on_signin
        async def flow_handler(_):
            calls.append("flow")

        mock_context.activity = token_exchange_activity
        mock_context.api.users.exchange_token.return_value = mock_token_response

        await handlers.sign_in_token_exchange(mock_context)

        assert calls == ["global", "flow"]

    @pytest.mark.asyncio
    async def test_flow_handler_error_does_not_stop_later_handlers_and_still_calls_next(
        self, oauth_handlers, mock_context, token_exchange_activity, mock_token_response
    ):
        # Per-flow handlers go through EventEmitter.emit_async, which isolates
        # them: a raising handler is logged, later handlers still run, and the
        # failure does not escape into the invoke response.
        flow = oauth_handlers.oauth_registry.add(OAuthFlow("test-connection"))
        calls = []
        oauth_handlers.event_emitter.emit_async.side_effect = lambda name, _: calls.append(f"global:{name}")

        @flow.on_signin
        async def failing(_):
            calls.append("flow:failing")
            raise RuntimeError("handler failed")

        @flow.on_signin
        async def still_runs(_):
            calls.append("flow:still_runs")

        mock_context.activity = token_exchange_activity
        mock_context.api.users.exchange_token.return_value = mock_token_response

        assert await oauth_handlers.sign_in_token_exchange(mock_context) is None

        assert calls == ["global:sign_in", "flow:failing", "flow:still_runs"]
        mock_context.next.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_duplicate_token_exchange_is_not_deduplicated_in_pr4(
        self, oauth_handlers, mock_context, token_exchange_activity, mock_token_response
    ):
        flow = oauth_handlers.oauth_registry.add(OAuthFlow("test-connection"))
        callback_count = 0

        @flow.on_signin
        async def on_signin(_):
            nonlocal callback_count
            callback_count += 1

        mock_context.activity = token_exchange_activity
        mock_context.api.users.exchange_token.return_value = mock_token_response

        await oauth_handlers.sign_in_token_exchange(mock_context)
        await oauth_handlers.sign_in_token_exchange(mock_context)

        assert mock_context.api.users.exchange_token.await_count == 2
        assert callback_count == 2

    @pytest.mark.asyncio
    async def test_verify_state_routes_to_pending_non_default_flow(
        self, oauth_handlers, mock_context, verify_state_activity, mock_token_response
    ):
        default = oauth_handlers.oauth_registry.add(OAuthFlow("test-connection"))
        github = oauth_handlers.oauth_registry.add(OAuthFlow("GitHub"))
        calls = []

        @default.on_signin
        async def on_default(_):
            calls.append("default")

        @github.on_signin
        async def on_github(event):
            calls.append(f"github:{event.connection_name}")

        state = create_pending_state(("github", time.time(), False))
        oauth_handlers.event_emitter.emit_async.side_effect = lambda name, event: calls.append(
            f"global:{name}:{event.connection_name}"
        )
        mock_context.activity = verify_state_activity
        mock_context.state = state
        mock_context.api.users.get_token.return_value = mock_token_response

        result = await oauth_handlers.sign_in_verify_state(mock_context)

        assert result is None
        assert calls == ["global:sign_in:GitHub", "github:GitHub"]
        params = mock_context.api.users.get_token.call_args.args[0]
        assert params.connection_name == "GitHub"
        assert state.user is not None
        assert pending_marker_keys(state) == set()

    @pytest.mark.asyncio
    async def test_verify_state_probes_pending_hints_then_remaining_flows(
        self, oauth_handlers, mock_context, verify_state_activity, mock_token_response
    ):
        graph = oauth_handlers.oauth_registry.add(OAuthFlow("Graph"))
        github = oauth_handlers.oauth_registry.add(OAuthFlow("GitHub"))
        calls = []

        @graph.on_signin
        async def on_graph(_):
            calls.append("graph")

        @github.on_signin
        async def on_github(event):
            calls.append(f"github:{event.connection_name}")

        state = create_pending_state(
            ("GitHub", time.time() - 10, False),
            ("graph", time.time(), True),
        )
        mock_context.activity = verify_state_activity
        mock_context.state = state
        mock_context.api.users.get_token.side_effect = [
            oauth_http_error(404, "Not found for Graph"),
            mock_token_response,
        ]

        result = await oauth_handlers.sign_in_verify_state(mock_context)

        assert result is None
        attempted = [call.args[0].connection_name for call in mock_context.api.users.get_token.await_args_list]
        assert attempted == ["Graph", "GitHub"]
        assert calls == ["github:GitHub"]
        assert state.user is not None
        assert pending_marker_keys(state) == {"__oauth:pending:graph", "__oauth:pending:sso:graph"}

    @pytest.mark.asyncio
    async def test_sso_failure_keeps_hint_so_button_click_still_routes_to_that_flow(
        self, oauth_handlers, mock_context, failure_activity, verify_state_activity, mock_token_response
    ):
        """After silent SSO fails, Teams shows the sign-in button on the same card.

        The follow-up verify-state carries no connection name, so the retired hint is what
        keeps it on GitHub instead of probing (and possibly mis-attributing to) Graph.
        """
        oauth_handlers.oauth_registry.add(OAuthFlow("Graph"))
        github = oauth_handlers.oauth_registry.add(OAuthFlow("GitHub"))
        calls = []

        @github.on_signin
        async def on_github(event):
            calls.append(f"github:{event.connection_name}")

        state = create_pending_state(("GitHub", time.time(), True))
        mock_context.state = state

        mock_context.activity = failure_activity
        await oauth_handlers.sign_in_failure(mock_context)

        mock_context.activity = verify_state_activity
        mock_context.api.users.get_token.return_value = mock_token_response
        result = await oauth_handlers.sign_in_verify_state(mock_context)

        assert result is None
        attempted = [call.args[0].connection_name for call in mock_context.api.users.get_token.await_args_list]
        assert attempted == ["GitHub"]
        assert calls == ["github:GitHub"]
        assert state.user is not None
        assert pending_marker_keys(state) == set()

    @pytest.mark.asyncio
    async def test_retired_sso_hint_does_not_attribute_a_second_failure(
        self, oauth_handlers, mock_context, failure_activity
    ):
        github = oauth_handlers.oauth_registry.add(OAuthFlow("GitHub"))
        calls = []

        @github.on_signin_failure
        async def on_github(event):
            calls.append(f"github:{event.connection_name}")

        mock_context.activity = failure_activity
        mock_context.state = create_pending_state(("GitHub", time.time(), True))

        await oauth_handlers.sign_in_failure(mock_context)
        assert calls == ["github:GitHub"]

        # Second failure: the hint's SSO marker is spent, so this falls back to the
        # notify-all-registered-flows path rather than re-attributing to GitHub.
        await oauth_handlers.sign_in_failure(mock_context)
        assert calls == ["github:GitHub", "github:GitHub"]
        assert mock_context.state.user is not None
        # The SSO marker is retired; the sign-in itself is still pending.
        assert pending_marker_keys(mock_context.state) == {"__oauth:pending:GitHub"}

    @pytest.mark.asyncio
    async def test_legacy_default_connection_hint_is_cleared_without_warning(
        self, oauth_handlers, mock_context, verify_state_activity, mock_token_response, caplog
    ):
        """A legacy app (no registered flows) must not log warnings on its happy path."""
        state = create_pending_state(("test-connection", time.time(), True))
        mock_context.activity = verify_state_activity
        mock_context.state = state
        mock_context.api.users.get_token.return_value = mock_token_response

        with caplog.at_level(logging.WARNING, logger="microsoft_teams.apps.oauth_flow"):
            result = await oauth_handlers.sign_in_verify_state(mock_context)

        assert result is None
        assert caplog.records == []
        params = mock_context.api.users.get_token.call_args.args[0]
        assert params.connection_name == "test-connection"
        assert state.user is not None
        assert pending_marker_keys(state) == set()

    @pytest.mark.asyncio
    async def test_sign_in_failure_routes_to_pending_flow_after_global_events(
        self, oauth_handlers, mock_context, failure_activity
    ):
        default = oauth_handlers.oauth_registry.add(OAuthFlow("test-connection"))
        github = oauth_handlers.oauth_registry.add(OAuthFlow("GitHub"))
        calls = []

        @default.on_signin_failure
        async def on_default(_):
            calls.append("default")

        @github.on_signin_failure
        async def on_github(event):
            calls.append(f"github:{event.connection_name}")

        state = create_pending_state(
            ("test-connection", time.time() - 10, True),
            ("GitHub", time.time(), True),
        )
        oauth_handlers.event_emitter.emit_async.side_effect = lambda name, event: calls.append(
            f"global:{name}:{getattr(event, 'connection_name', None)}"
        )
        mock_context.activity = failure_activity
        mock_context.state = state

        result = await oauth_handlers.sign_in_failure(mock_context)

        assert result is None
        assert calls == [
            "global:error:None",
            "global:sign_in_failure:GitHub",
            "github:GitHub",
        ]
        assert state.user is not None
        # The failed connection keeps its hint (the card's sign-in button is still live) but
        # loses its SSO marker so it cannot re-attribute a second failure.
        assert pending_marker_keys(state) == {
            "__oauth:pending:test-connection",
            "__oauth:pending:sso:test-connection",
            "__oauth:pending:GitHub",
        }

    @pytest.mark.asyncio
    async def test_sign_in_failure_preserves_replacement_hint_created_by_global_handler(
        self, oauth_handlers, mock_context, failure_activity
    ):
        github = oauth_handlers.oauth_registry.add(OAuthFlow("GitHub"))
        state = create_pending_state(("GitHub", time.time(), True))
        oauth_handlers.event_emitter = EventEmitter()

        async def replace_hint(event):
            assert event.connection_name == "GitHub"
            assert state.user is not None
            assert pending_marker_keys(state) == {"__oauth:pending:GitHub"}
            state.user["__oauth:pending:GitHub"] = datetime.now(timezone.utc).isoformat()
            state.user["__oauth:pending:sso:GitHub"] = state.user["__oauth:pending:GitHub"]

        oauth_handlers.event_emitter.on("sign_in_failure", replace_hint)
        mock_context.activity = failure_activity
        mock_context.state = state

        await oauth_handlers.sign_in_failure(mock_context)

        assert state.user is not None
        assert pending_marker_keys(state) == {
            f"__oauth:pending:{github.connection_name}",
            f"__oauth:pending:sso:{github.connection_name}",
        }

    @pytest.mark.asyncio
    async def test_sign_in_failure_ignores_more_recent_non_sso_hint(
        self, oauth_handlers, mock_context, failure_activity
    ):
        graph = oauth_handlers.oauth_registry.add(OAuthFlow("Graph"))
        github = oauth_handlers.oauth_registry.add(OAuthFlow("GitHub"))
        calls = []

        @graph.on_signin_failure
        async def on_graph(event):
            calls.append(f"graph:{event.connection_name}")

        @github.on_signin_failure
        async def on_github(_):
            calls.append("github")

        mock_context.activity = failure_activity
        mock_context.state = create_pending_state(
            ("Graph", time.time() - 10, True),
            ("GitHub", time.time(), False),
        )

        await oauth_handlers.sign_in_failure(mock_context)

        assert calls == ["graph:Graph"]

    @pytest.mark.asyncio
    async def test_sign_in_failure_without_attribution_notifies_all_registered_flows(
        self, oauth_handlers, mock_context, failure_activity
    ):
        graph = oauth_handlers.oauth_registry.add(OAuthFlow("Graph"))
        github = oauth_handlers.oauth_registry.add(OAuthFlow("GitHub"))
        calls = []
        oauth_handlers.event_emitter.emit_async.side_effect = lambda name, event: calls.append(
            f"global:{name}:{getattr(event, 'connection_name', None)}"
        )

        @graph.on_signin_failure
        async def on_graph(event):
            calls.append(f"graph:{event.connection_name}")

        @github.on_signin_failure
        async def on_github(event):
            calls.append(f"github:{event.connection_name}")

        mock_context.activity = failure_activity
        mock_context.state = None

        await oauth_handlers.sign_in_failure(mock_context)

        assert calls == [
            "global:error:None",
            # Registered flows exist but nothing attributed the callback, so the
            # failed connection is unknown rather than the default. Fan-out still
            # reaches every flow, each with its own canonical name.
            "global:sign_in_failure:None",
            "graph:Graph",
            "github:GitHub",
        ]

    @pytest.mark.asyncio
    async def test_legacy_mode_without_registered_flows_reports_default_connection(
        self, oauth_handlers, mock_context, failure_activity
    ):
        # No flows registered, so the default connection is the only connection
        # there is. Naming it is accurate here, unlike the registered case.
        calls = []
        oauth_handlers.event_emitter.emit_async.side_effect = lambda name, event: calls.append(
            f"global:{name}:{getattr(event, 'connection_name', None)}"
        )
        mock_context.activity = failure_activity
        mock_context.state = None

        with patch("microsoft_teams.apps.app_oauth.record_oauth_operation") as record:
            assert await oauth_handlers.sign_in_failure(mock_context) is None

        assert calls == ["global:error:None", "global:sign_in_failure:test-connection"]
        assert record.call_args[0][0] == "test-connection"

    @pytest.mark.asyncio
    async def test_unattributed_failure_telemetry_does_not_name_the_default_connection(
        self, oauth_handlers, mock_context, failure_activity
    ):
        # The whole point of reporting None: a dashboard must not show
        # "test-connection" failing when the failed connection is unknown.
        oauth_handlers.oauth_registry.add(OAuthFlow("Graph"))
        oauth_handlers.oauth_registry.add(OAuthFlow("GitHub"))
        mock_context.activity = failure_activity
        mock_context.state = None

        with patch("microsoft_teams.apps.app_oauth.record_oauth_operation") as record:
            assert await oauth_handlers.sign_in_failure(mock_context) is None

        assert record.call_args[0][0] is None

    @pytest.mark.asyncio
    async def test_attributed_failure_telemetry_names_the_resolved_flow(
        self, oauth_handlers, mock_context, failure_activity
    ):
        oauth_handlers.oauth_registry.add(OAuthFlow("test-connection"))
        oauth_handlers.oauth_registry.add(OAuthFlow("GitHub"))
        mock_context.activity = failure_activity
        mock_context.state = create_pending_state(
            ("test-connection", time.time() - 10, True),
            ("GitHub", time.time(), True),
        )

        with patch("microsoft_teams.apps.app_oauth.record_oauth_operation") as record:
            assert await oauth_handlers.sign_in_failure(mock_context) is None

        assert record.call_args[0][0] == "GitHub"

    @pytest.mark.asyncio
    async def test_registered_default_flow_handles_connectionless_callbacks_without_state(
        self, oauth_handlers, mock_context, verify_state_activity, failure_activity, mock_token_response
    ):
        flow = oauth_handlers.oauth_registry.add(OAuthFlow("Test-Connection"))
        calls = []

        @flow.on_signin
        async def on_signin(event):
            calls.append(f"success:{event.connection_name}")

        @flow.on_signin_failure
        async def on_failure(event):
            calls.append(f"failure:{event.connection_name}")

        mock_context.state = None
        mock_context.activity = verify_state_activity
        mock_context.api.users.get_token.return_value = mock_token_response
        await oauth_handlers.sign_in_verify_state(mock_context)
        mock_context.activity = failure_activity
        await oauth_handlers.sign_in_failure(mock_context)

        assert calls == ["success:Test-Connection", "failure:Test-Connection"]

    @pytest.mark.parametrize(
        "pending_kind",
        ["non-string", "not-iso", "unknown", "stale", "future"],
    )
    @pytest.mark.asyncio
    async def test_invalid_pending_attribution_falls_back_to_default_and_is_cleared(
        self,
        pending_kind,
        oauth_handlers,
        mock_context,
        verify_state_activity,
        mock_token_response,
        caplog,
    ):
        default = oauth_handlers.oauth_registry.add(OAuthFlow("Test-Connection"))
        github = oauth_handlers.oauth_registry.add(OAuthFlow("GitHub"))
        calls = []

        @default.on_signin
        async def on_default(event):
            calls.append(f"default:{event.connection_name}")

        @github.on_signin
        async def on_github(_):
            calls.append("github")

        now = time.time()
        if pending_kind == "non-string":
            # A list is not a timestamp.
            pending: Any = ["GitHub"]
        elif pending_kind == "not-iso":
            pending = "not-a-timestamp"
        elif pending_kind == "unknown":
            pending = iso(now)
        elif pending_kind == "stale":
            pending = iso(now - 301)
        else:
            pending = iso(now + 61)

        connection = "Missing" if pending_kind == "unknown" else "GitHub"
        state = create_turn_state(
            {
                f"__oauth:pending:{connection}": pending,
                f"__oauth:pending:sso:{connection}": pending,
            }
        )
        mock_context.activity = verify_state_activity
        mock_context.state = state
        mock_context.api.users.get_token.return_value = mock_token_response

        with caplog.at_level(logging.DEBUG):
            await oauth_handlers.sign_in_verify_state(mock_context)

        assert calls == ["default:Test-Connection"]
        params = mock_context.api.users.get_token.call_args.args[0]
        assert params.connection_name == "Test-Connection"
        assert state.user is not None
        assert pending_marker_keys(state) == set()
        assert "Discarding" in caplog.text
        warnings = [record for record in caplog.records if record.levelno >= logging.WARNING]
        if pending_kind == "unknown":
            # A hint for an unregistered connection is normal (every legacy `ctx.sign_in()`
            # produces one), so it is discarded quietly.
            assert warnings == []
        else:
            # Corrupt or impossible state is worth surfacing.
            assert warnings != []

    @pytest.mark.asyncio
    async def test_verify_state_without_attribution_probes_registered_flow(
        self, oauth_handlers, mock_context, verify_state_activity, mock_token_response
    ):
        github = oauth_handlers.oauth_registry.add(OAuthFlow("GitHub"))
        called = False

        @github.on_signin
        async def on_github(_):
            nonlocal called
            called = True

        mock_context.activity = verify_state_activity
        mock_context.state = None
        mock_context.api.users.get_token.return_value = mock_token_response

        await oauth_handlers.sign_in_verify_state(mock_context)

        params = mock_context.api.users.get_token.call_args.args[0]
        assert params.connection_name == "GitHub"
        assert called is True
        emitted_event = oauth_handlers.event_emitter.emit_async.call_args.args[1]
        assert emitted_event.connection_name == "GitHub"

    @pytest.mark.asyncio
    async def test_verify_state_probe_falls_back_to_legacy_default(
        self, oauth_handlers, mock_context, verify_state_activity, mock_token_response
    ):
        github = oauth_handlers.oauth_registry.add(OAuthFlow("GitHub"))
        called = False

        @github.on_signin
        async def on_github(_):
            nonlocal called
            called = True

        mock_context.activity = verify_state_activity
        mock_context.state = None
        mock_context.api.users.get_token.side_effect = [
            oauth_http_error(404, "Not found for GitHub"),
            mock_token_response,
        ]

        await oauth_handlers.sign_in_verify_state(mock_context)

        attempted = [call.args[0].connection_name for call in mock_context.api.users.get_token.await_args_list]
        assert attempted == ["GitHub", "test-connection"]
        assert called is False
        emitted_event = oauth_handlers.event_emitter.emit_async.call_args.args[1]
        assert emitted_event.connection_name == "test-connection"

    @pytest.mark.asyncio
    async def test_verify_state_non_404_service_error_keeps_status_with_pending_flow(
        self, oauth_handlers, mock_context, verify_state_activity
    ):
        github = oauth_handlers.oauth_registry.add(OAuthFlow("GitHub"))
        called = False

        @github.on_signin
        async def on_github(_):
            nonlocal called
            called = True

        oauth_handlers.oauth_registry.add(OAuthFlow("test-connection"))
        state = create_pending_state(("github", time.time(), True))
        response = Mock(spec=Response)
        response.status_code = 503
        mock_context.api.users.get_token.side_effect = HTTPStatusError(
            "Unavailable",
            request=Mock(spec=Request),
            response=response,
        )
        mock_context.activity = verify_state_activity
        mock_context.state = state

        result = await oauth_handlers.sign_in_verify_state(mock_context)

        assert isinstance(result, InvokeResponse)
        assert result.status == 503
        assert called is False
        assert mock_context.api.users.get_token.await_count == 1

    def test_oauth_handlers_initialization(self, mock_event_emitter):
        """Test OauthHandlers initialization."""
        registry = OAuthFlowRegistry()
        handlers = OauthHandlers("my-connection", mock_event_emitter, registry)

        assert handlers.default_connection_name == "my-connection"
        assert handlers.event_emitter == mock_event_emitter
        assert handlers.oauth_registry is registry


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
        return ActivityRouter()

    @pytest.fixture
    def processor(self, router):
        """Create an ActivityProcessor for middleware chain execution."""
        return ActivityProcessor(
            router=router,
            id="bot-456",
            storage=LocalStorage(),
            default_connection_name="graph",
            http_client=MagicMock(),
            token_provider=MagicMock(spec=AppTokenProvider),
            get_app_graph_token=AsyncMock(return_value=None),
            api_client_settings=None,
            cloud=PUBLIC,
        )

    @staticmethod
    def _make_ctx(activity):
        """Build a minimal ActivityContext for chain execution."""
        return ActivityContext(
            activity=activity,
            app_id="bot-456",
            storage=MagicMock(),
            api=MagicMock(),
            user_token=None,
            conversation_ref=MagicMock(),
            is_signed_in=False,
            connection_name="graph",
            app_token=MagicMock(),
            cloud=PUBLIC,
        )

    @pytest.mark.asyncio
    async def test_system_default_handler_fires_alone(self, router, processor, failure_activity):
        """System default fires when no developer handler is registered."""
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
