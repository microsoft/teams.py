"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.

Teams fans ``signin/tokenExchange`` out to every signed-in client endpoint, so the
same exchange reaches the bot several times. These tests pin down the resulting
deduplication contract end to end through the public handler entry points.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import HTTPStatusError, Request, Response
from microsoft_teams.api import (
    InvokeResponse,
    SignInFailureInvokeActivity,
    SignInTokenExchangeInvokeActivity,
    SignInVerifyStateInvokeActivity,
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
from microsoft_teams.apps.oauth_flow import OAuthFlow, OAuthFlowRegistry
from microsoft_teams.apps.routing import ActivityContext
from microsoft_teams.apps.state import TurnState, TurnStateContainer
from microsoft_teams.common import EventEmitter

# pyright: basic

DEDUP_TTL_SECONDS = 5 * 60
"""Mirror of the production TTL. Duplicated rather than imported so a silent change
to the production value shows up here as a failure instead of passing vacuously."""

DEDUP_MAX_ENTRIES = 1000
"""Mirror of the production cap on the in-memory completed-marker set."""

CONNECTION_NAME = "test-connection"
EXCHANGE_STATE_KEY_PREFIX = "__oauth:exchange:"


def iso(epoch_seconds: float) -> str:
    """Render an epoch as the ISO 8601 UTC string a marker is stored as.

    Mirrors the production storage boundary rather than importing it, so a change to
    the persisted format surfaces here as a failure instead of passing vacuously.
    """
    return datetime.fromtimestamp(epoch_seconds, tz=timezone.utc).isoformat()


def token_response() -> TokenResponse:
    return TokenResponse(connection_name=CONNECTION_NAME, token="access-token", expiration="2024-12-31T23:59:59Z")


def oauth_http_error(status: int, message: str = "boom") -> HTTPStatusError:
    request = Request("GET", "https://token.example")
    response = Response(status, request=request)
    return HTTPStatusError(message, request=request, response=response)


def exchange_activity(exchange_id: str = "exchange-1", token: str = "sso-token") -> SignInTokenExchangeInvokeActivity:
    return SignInTokenExchangeInvokeActivity(
        type="invoke",
        id="activity-789",
        from_=Account(id="user-123", name="Test User", role="user"),
        recipient=Account(id="bot-456", name="Test Bot", role="bot"),
        conversation=ConversationAccount(id="conv-456", conversation_type="personal"),
        channel_id="msteams",
        name="signin/tokenExchange",
        value=SignInExchangeToken(id=exchange_id, connection_name=CONNECTION_NAME, token=token),
    )


def verify_state_activity() -> SignInVerifyStateInvokeActivity:
    return SignInVerifyStateInvokeActivity(
        type="invoke",
        id="activity-789",
        from_=Account(id="user-123", name="Test User", role="user"),
        recipient=Account(id="bot-456", name="Test Bot", role="bot"),
        conversation=ConversationAccount(id="conv-456", conversation_type="personal"),
        channel_id="msteams",
        name="signin/verifyState",
        value=SignInStateVerifyQuery(state="verify-code"),
    )


def failure_activity() -> SignInFailureInvokeActivity:
    return SignInFailureInvokeActivity(
        type="invoke",
        id="activity-789",
        from_=Account(id="user-123", name="Test User", role="user"),
        recipient=Account(id="bot-456", name="Test Bot", role="bot"),
        conversation=ConversationAccount(id="conv-456", conversation_type="personal"),
        channel_id="msteams",
        name="signin/failure",
        value=SignInFailure(code="invokeerror", message="nope"),
    )


def make_api(*, exchange: Any = None, get_token: Any = None) -> MagicMock:
    """A stand-in ``ctx.api``. Shared between contexts so call counts span requests."""
    api = MagicMock()
    api.users.exchange_token = exchange if exchange is not None else AsyncMock(return_value=token_response())
    api.users.get_token = get_token if get_token is not None else AsyncMock(return_value=token_response())
    return api


def slow_exchange(*outcomes: Any, delay: float = 0.01) -> AsyncMock:
    """An ``exchange_token`` mock that yields to the event loop before answering.

    The suspension is what lets a second concurrent request reach the dedup gate while
    the first exchange is still in flight.
    """
    queued: List[Any] = list(outcomes) or [token_response()]

    async def _exchange(_params: Any) -> Any:
        await asyncio.sleep(delay)
        outcome = queued.pop(0) if len(queued) > 1 else queued[0]
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    return AsyncMock(side_effect=_exchange)


def make_context(activity: Any, api: MagicMock, state: Optional[TurnStateContainer] = None) -> MagicMock:
    ctx = MagicMock(spec=ActivityContext)
    ctx.activity = activity
    ctx.api = api
    ctx.logger = MagicMock()
    ctx.next = AsyncMock()
    ctx.state = state
    return ctx


def make_state() -> TurnStateContainer:
    return TurnStateContainer(
        conversation=TurnState(),
        conversation_id="conv-456",
        user=TurnState(),
        user_id="user-123",
    )


def make_handlers() -> tuple[OauthHandlers, MagicMock, OAuthFlow]:
    emitter = MagicMock(spec=EventEmitter)
    registry = OAuthFlowRegistry()
    flow = registry.add(OAuthFlow(CONNECTION_NAME))
    return OauthHandlers(CONNECTION_NAME, emitter, registry), emitter, flow


def status_of(result: Any) -> int:
    """The status Teams ends up seeing.

    The owning request signals success by returning ``None``, which the activity
    processor materializes as a 200; duplicates return that 200 explicitly.
    """
    return result.status if isinstance(result, InvokeResponse) else 200


def emitted(emitter: MagicMock, name: str) -> List[Any]:
    return [call.args[1] for call in emitter.emit_async.await_args_list if call.args[0] == name]


class TestConcurrentTokenExchangeDedup:
    @pytest.mark.asyncio
    async def test_concurrent_duplicates_run_sign_in_side_effects_exactly_once(self):
        handlers, emitter, flow = make_handlers()
        signin_calls: List[str] = []

        @flow.on_signin
        async def on_signin(event):
            signin_calls.append(event.connection_name)

        api = make_api(exchange=slow_exchange())
        first = make_context(exchange_activity(), api)
        second = make_context(exchange_activity(), api)

        results = await asyncio.gather(
            handlers.sign_in_token_exchange(first),
            handlers.sign_in_token_exchange(second),
        )

        assert [status_of(result) for result in results] == [200, 200]
        assert api.users.exchange_token.await_count == 1
        assert len(emitted(emitter, "sign_in")) == 1
        assert signin_calls == [CONNECTION_NAME]
        # The winner runs the middleware chain; the duplicate is a no-op, so `next`
        # fires once across the pair rather than once per request.
        assert sorted([first.next.await_count, second.next.await_count]) == [0, 1]

    @pytest.mark.asyncio
    async def test_concurrent_duplicates_mirror_the_original_failure(self):
        handlers, emitter, flow = make_handlers()

        @flow.on_signin
        async def on_signin(_event):
            pytest.fail("sign-in handlers must not run when the exchange fails")

        api = make_api(exchange=slow_exchange(oauth_http_error(400, "bad exchange")))
        first = make_context(exchange_activity("exchange-fail"), api)
        second = make_context(exchange_activity("exchange-fail"), api)

        results = await asyncio.gather(
            handlers.sign_in_token_exchange(first),
            handlers.sign_in_token_exchange(second),
        )

        assert api.users.exchange_token.await_count == 1
        assert [status_of(result) for result in results] == [412, 412]
        for result in results:
            assert isinstance(result, InvokeResponse)
            assert result.body is not None
            assert result.body.id == "exchange-fail"
            assert result.body.connection_name == CONNECTION_NAME
        assert emitted(emitter, "sign_in") == []

    @pytest.mark.asyncio
    async def test_broken_sign_in_handler_does_not_break_dedup(self):
        """A raising ``on_signin`` listener is contained by the flow.

        Handler isolation means one broken listener must not turn a successful
        callback into a failed invoke response -- so neither the owner nor its
        duplicate fails, and the token is still exchanged exactly once.
        """
        handlers, emitter, flow = make_handlers()

        @flow.on_signin
        async def on_signin(_event):
            raise RuntimeError("handler failed")

        api = make_api(exchange=slow_exchange())
        first = make_context(exchange_activity("exchange-raise"), api)
        second = make_context(exchange_activity("exchange-raise"), api)

        results = await asyncio.gather(
            handlers.sign_in_token_exchange(first),
            handlers.sign_in_token_exchange(second),
            return_exceptions=True,
        )

        assert api.users.exchange_token.await_count == 1
        assert not any(isinstance(result, BaseException) for result in results)
        assert [status_of(result) for result in results] == [200, 200]
        assert len(emitted(emitter, "sign_in")) == 1

    @pytest.mark.asyncio
    async def test_duplicate_arriving_during_sign_in_callbacks_awaits_the_owner(self):
        """The completed marker is stamped the moment the token is redeemed.

        A duplicate that lands in the window between redemption and the sign-in
        callbacks finishing must still mirror the owner, not answer ahead of it.
        """
        handlers, _emitter, flow = make_handlers()
        handler_started = asyncio.Event()
        release_handler = asyncio.Event()
        finished: List[str] = []

        @flow.on_signin
        async def on_signin(_event):
            handler_started.set()
            await release_handler.wait()
            finished.append("handler")

        api = make_api()
        first = make_context(exchange_activity(), api)
        second = make_context(exchange_activity(), api)

        owner = asyncio.create_task(handlers.sign_in_token_exchange(first))
        await handler_started.wait()
        duplicate = asyncio.create_task(handlers.sign_in_token_exchange(second))
        await asyncio.sleep(0)

        # Still parked on the owner's future: the marker alone must not let it answer.
        assert not duplicate.done()
        assert finished == []
        release_handler.set()

        results = await asyncio.gather(owner, duplicate)

        assert api.users.exchange_token.await_count == 1
        # The owner's callbacks ran to completion before the duplicate was answered.
        assert finished == ["handler"]
        assert [status_of(result) for result in results] == [200, 200]

    @pytest.mark.asyncio
    async def test_concurrent_exchanges_with_distinct_ids_both_run(self):
        handlers, emitter, _flow = make_handlers()
        api = make_api(exchange=slow_exchange())
        first = make_context(exchange_activity("exchange-a"), api)
        second = make_context(exchange_activity("exchange-b"), api)

        results = await asyncio.gather(
            handlers.sign_in_token_exchange(first),
            handlers.sign_in_token_exchange(second),
        )

        assert results == [None, None]
        assert api.users.exchange_token.await_count == 2
        assert len(emitted(emitter, "sign_in")) == 2
        assert first.next.await_count == 1
        assert second.next.await_count == 1

    @pytest.mark.asyncio
    async def test_concurrent_exchanges_without_an_id_are_never_collapsed(self):
        """An empty id is not a shared key: two unrelated sign-ins must both proceed."""
        handlers, emitter, _flow = make_handlers()
        api = make_api(exchange=slow_exchange())
        first = make_context(exchange_activity("", token="sso-token-a"), api)
        second = make_context(exchange_activity("", token="sso-token-b"), api)

        results = await asyncio.gather(
            handlers.sign_in_token_exchange(first),
            handlers.sign_in_token_exchange(second),
        )

        assert results == [None, None]
        assert api.users.exchange_token.await_count == 2
        exchanged = [call.args[0].exchange_request.token for call in api.users.exchange_token.await_args_list]
        assert sorted(exchanged) == ["sso-token-a", "sso-token-b"]
        assert len(emitted(emitter, "sign_in")) == 2
        assert first.next.await_count == 1
        assert second.next.await_count == 1


class TestLateTokenExchangeDedup:
    @pytest.mark.asyncio
    async def test_late_duplicate_is_a_200_no_op(self):
        handlers, emitter, flow = make_handlers()
        signin_calls: List[str] = []

        @flow.on_signin
        async def on_signin(event):
            signin_calls.append(event.connection_name)

        api = make_api()
        first = make_context(exchange_activity(), api)
        second = make_context(exchange_activity(), api)

        assert await handlers.sign_in_token_exchange(first) is None
        late = await handlers.sign_in_token_exchange(second)

        assert isinstance(late, InvokeResponse)
        assert late.status == 200
        assert late.body is None
        assert api.users.exchange_token.await_count == 1
        assert signin_calls == [CONNECTION_NAME]
        assert len(emitted(emitter, "sign_in")) == 1
        assert first.next.await_count == 1
        assert second.next.await_count == 0

    @pytest.mark.asyncio
    async def test_sequential_exchanges_with_distinct_ids_both_run(self):
        handlers, emitter, _flow = make_handlers()
        api = make_api()

        first = make_context(exchange_activity("exchange-a"), api)
        second = make_context(exchange_activity("exchange-b"), api)
        assert await handlers.sign_in_token_exchange(first) is None
        assert await handlers.sign_in_token_exchange(second) is None

        assert api.users.exchange_token.await_count == 2
        assert len(emitted(emitter, "sign_in")) == 2

    @pytest.mark.asyncio
    async def test_sequential_exchanges_without_an_id_are_never_collapsed(self):
        handlers, emitter, _flow = make_handlers()
        api = make_api()

        first = make_context(exchange_activity(""), api)
        second = make_context(exchange_activity(""), api)
        assert await handlers.sign_in_token_exchange(first) is None
        assert await handlers.sign_in_token_exchange(second) is None

        assert api.users.exchange_token.await_count == 2
        assert len(emitted(emitter, "sign_in")) == 2
        assert first.next.await_count == 1
        assert second.next.await_count == 1

    @pytest.mark.asyncio
    async def test_dedup_works_without_state_configured(self):
        handlers, _emitter, _flow = make_handlers()
        api = make_api()
        first = make_context(exchange_activity(), api, state=None)
        second = make_context(exchange_activity(), api, state=None)

        await handlers.sign_in_token_exchange(first)
        late = await handlers.sign_in_token_exchange(second)

        assert status_of(late) == 200
        assert api.users.exchange_token.await_count == 1

    @pytest.mark.asyncio
    async def test_a_second_app_instance_does_not_share_in_memory_dedup(self):
        """Guards against the marker set living in module scope instead of per app."""
        first_handlers, _first_emitter, _first_flow = make_handlers()
        second_handlers, _second_emitter, _second_flow = make_handlers()
        api = make_api()

        await first_handlers.sign_in_token_exchange(make_context(exchange_activity(), api))
        assert await second_handlers.sign_in_token_exchange(make_context(exchange_activity(), api)) is None

        assert api.users.exchange_token.await_count == 2

    @pytest.mark.asyncio
    async def test_sign_in_handler_failure_still_marks_the_exchange_as_spent(self):
        """The exchange token is single-use, so a duplicate could never redeem it again."""
        handlers, _emitter, flow = make_handlers()

        @flow.on_signin
        async def on_signin(_event):
            raise RuntimeError("handler failed")

        api = make_api()
        first = make_context(exchange_activity(), api)
        second = make_context(exchange_activity(), api)

        # Handler isolation contains the failure, so the exchange still succeeds --
        # but the marker must be stamped either way, which is what the duplicate proves.
        assert await handlers.sign_in_token_exchange(first) is None
        # PR4 guarantee: the owning request still advances the middleware chain.
        assert first.next.await_count == 1

        assert status_of(await handlers.sign_in_token_exchange(second)) == 200
        assert api.users.exchange_token.await_count == 1


class TestTokenExchangeDedupFailures:
    @pytest.mark.asyncio
    async def test_failed_exchange_can_be_retried_with_the_same_id(self):
        """The in-flight entry is released on settle and a failure is never marked."""
        handlers, emitter, _flow = make_handlers()
        api = make_api(exchange=AsyncMock(side_effect=[oauth_http_error(400, "bad"), token_response()]))

        first = make_context(exchange_activity("exchange-retry"), api)
        second = make_context(exchange_activity("exchange-retry"), api)

        failed = await handlers.sign_in_token_exchange(first)
        assert status_of(failed) == 412

        assert await handlers.sign_in_token_exchange(second) is None
        assert api.users.exchange_token.await_count == 2
        assert len(emitted(emitter, "sign_in")) == 1
        assert first.next.await_count == 1
        assert second.next.await_count == 1

    @pytest.mark.asyncio
    async def test_unexpected_service_error_keeps_its_status_and_is_not_marked_complete(self):
        handlers, emitter, _flow = make_handlers()
        api = make_api(exchange=AsyncMock(side_effect=[oauth_http_error(503, "unavailable"), token_response()]))

        first = make_context(exchange_activity("exchange-503"), api)
        second = make_context(exchange_activity("exchange-503"), api)

        result = await handlers.sign_in_token_exchange(first)

        assert isinstance(result, InvokeResponse)
        assert result.status == 503
        assert result.body is None
        assert len(emitted(emitter, "error")) == 1
        assert emitted(emitter, "sign_in") == []

        assert await handlers.sign_in_token_exchange(second) is None
        assert api.users.exchange_token.await_count == 2
        assert len(emitted(emitter, "sign_in")) == 1

    @pytest.mark.asyncio
    async def test_concurrent_duplicate_mirrors_an_unexpected_service_status(self):
        handlers, emitter, _flow = make_handlers()
        api = make_api(exchange=slow_exchange(oauth_http_error(503, "unavailable")))
        first = make_context(exchange_activity("exchange-503"), api)
        second = make_context(exchange_activity("exchange-503"), api)

        results = await asyncio.gather(
            handlers.sign_in_token_exchange(first),
            handlers.sign_in_token_exchange(second),
        )

        assert [status_of(result) for result in results] == [503, 503]
        assert api.users.exchange_token.await_count == 1
        # Only the request that actually talked to the service reports the error.
        assert len(emitted(emitter, "error")) == 1


class TestTokenExchangeDedupState:
    @pytest.mark.asyncio
    async def test_completion_is_persisted_under_the_reserved_conversation_key(self):
        handlers, _emitter, _flow = make_handlers()
        api = make_api()
        state = make_state()

        await handlers.sign_in_token_exchange(make_context(exchange_activity(), api, state))

        marker = state.conversation[f"{EXCHANGE_STATE_KEY_PREFIX}exchange-1"]
        # A bare ISO 8601 UTC string, matching the value shape the C# SDK stores.
        assert isinstance(marker, str)
        assert datetime.fromisoformat(marker).tzinfo is not None
        # Conversation scope, not user scope — a duplicate can arrive from any of the
        # user's clients but always on the same conversation.
        assert state.user is not None
        assert f"{EXCHANGE_STATE_KEY_PREFIX}exchange-1" not in state.user

    @pytest.mark.asyncio
    async def test_persisted_marker_dedups_across_app_instances(self):
        first_handlers, _first_emitter, _first_flow = make_handlers()
        second_handlers, second_emitter, _second_flow = make_handlers()
        api = make_api()
        state = make_state()

        await first_handlers.sign_in_token_exchange(make_context(exchange_activity(), api, state))
        late = make_context(exchange_activity(), api, state)
        result = await second_handlers.sign_in_token_exchange(late)

        assert status_of(result) == 200
        assert api.users.exchange_token.await_count == 1
        assert emitted(second_emitter, "sign_in") == []
        assert late.next.await_count == 0

    @pytest.mark.asyncio
    async def test_failure_is_not_persisted_as_a_completion(self):
        handlers, _emitter, _flow = make_handlers()
        api = make_api(exchange=AsyncMock(side_effect=oauth_http_error(400, "bad")))
        state = make_state()

        await handlers.sign_in_token_exchange(make_context(exchange_activity(), api, state))

        assert [key for key in state.conversation if key.startswith(EXCHANGE_STATE_KEY_PREFIX)] == []

    @pytest.mark.asyncio
    async def test_concurrent_duplicate_stamps_the_marker_into_its_own_snapshot(self):
        """Each turn saves its own snapshot, last-write-wins.

        An unstamped duplicate snapshot would erase the owner's freshly written marker
        if its save happened to land last.
        """
        handlers, _emitter, _flow = make_handlers()
        api = make_api(exchange=slow_exchange())
        owner_state = make_state()
        waiter_state = make_state()

        await asyncio.gather(
            handlers.sign_in_token_exchange(make_context(exchange_activity(), api, owner_state)),
            handlers.sign_in_token_exchange(make_context(exchange_activity(), api, waiter_state)),
        )

        key = f"{EXCHANGE_STATE_KEY_PREFIX}exchange-1"
        assert isinstance(owner_state.conversation[key], str)
        assert isinstance(waiter_state.conversation[key], str)
        assert api.users.exchange_token.await_count == 1

    @pytest.mark.asyncio
    async def test_late_duplicate_stamps_the_marker_into_its_own_snapshot(self):
        handlers, _emitter, _flow = make_handlers()
        api = make_api()
        owner_state = make_state()
        late_state = make_state()

        await handlers.sign_in_token_exchange(make_context(exchange_activity(), api, owner_state))
        await handlers.sign_in_token_exchange(make_context(exchange_activity(), api, late_state))

        key = f"{EXCHANGE_STATE_KEY_PREFIX}exchange-1"
        assert isinstance(late_state.conversation[key], str)
        assert api.users.exchange_token.await_count == 1

    @pytest.mark.asyncio
    async def test_duplicate_does_not_extend_an_existing_marker(self, monkeypatch):
        """Re-stamping a snapshot that already has the marker would push out its TTL."""
        handlers, _emitter, _flow = make_handlers()
        api = make_api()
        state = make_state()
        clock = {"now": 1_000.0}
        monkeypatch.setattr("microsoft_teams.apps.app_oauth.time", lambda: clock["now"])
        monkeypatch.setattr("microsoft_teams.apps.oauth_state.time", lambda: clock["now"])

        await handlers.sign_in_token_exchange(make_context(exchange_activity(), api, state))
        clock["now"] += 60
        await handlers.sign_in_token_exchange(make_context(exchange_activity(), api, state))

        assert state.conversation[f"{EXCHANGE_STATE_KEY_PREFIX}exchange-1"] == iso(1_000.0)

    @pytest.mark.parametrize(
        "corrupt",
        [
            "not-an-iso-timestamp",
            "",
            123,
            None,
            True,
            [],
            {"version": 1, "completed_at": 1.0},
        ],
        ids=[
            "unparseable-string",
            "empty-string",
            "number",
            "null",
            "bool",
            "list",
            "legacy-dict-format",
        ],
    )
    @pytest.mark.asyncio
    async def test_corrupt_persisted_marker_does_not_crash_the_turn(self, corrupt):
        handlers, emitter, _flow = make_handlers()
        api = make_api()
        state = make_state()
        state.conversation[f"{EXCHANGE_STATE_KEY_PREFIX}exchange-1"] = corrupt

        result = await handlers.sign_in_token_exchange(make_context(exchange_activity(), api, state))

        assert result is None
        assert api.users.exchange_token.await_count == 1
        assert len(emitted(emitter, "sign_in")) == 1
        # The unusable value is replaced by a well-formed marker.
        assert isinstance(state.conversation[f"{EXCHANGE_STATE_KEY_PREFIX}exchange-1"], str)

    @pytest.mark.asyncio
    async def test_corrupt_persisted_marker_is_logged(self, caplog):
        handlers, _emitter, _flow = make_handlers()
        api = make_api()
        state = make_state()
        state.conversation[f"{EXCHANGE_STATE_KEY_PREFIX}exchange-1"] = "not-an-iso-timestamp"

        with caplog.at_level(logging.WARNING, logger="microsoft_teams.apps.oauth_state"):
            await handlers.sign_in_token_exchange(make_context(exchange_activity(), api, state))

        assert "malformed completed OAuth token exchange state" in caplog.text

    @pytest.mark.asyncio
    async def test_marker_leaves_unrelated_state_untouched(self):
        handlers, _emitter, _flow = make_handlers()
        api = make_api()
        state = make_state()
        state.conversation["app-data"] = {"counter": 1}

        await handlers.sign_in_token_exchange(make_context(exchange_activity(), api, state))

        assert state.conversation["app-data"] == {"counter": 1}


class TestTokenExchangeDedupExpiry:
    @pytest.mark.asyncio
    async def test_marker_expires_after_the_ttl(self, monkeypatch):
        handlers, emitter, _flow = make_handlers()
        api = make_api()
        state = make_state()
        clock = {"now": 1_000.0}
        monkeypatch.setattr("microsoft_teams.apps.app_oauth.time", lambda: clock["now"])
        monkeypatch.setattr("microsoft_teams.apps.oauth_state.time", lambda: clock["now"])

        await handlers.sign_in_token_exchange(make_context(exchange_activity(), api, state))

        clock["now"] += DEDUP_TTL_SECONDS - 1
        assert status_of(await handlers.sign_in_token_exchange(make_context(exchange_activity(), api, state))) == 200
        assert api.users.exchange_token.await_count == 1

        clock["now"] += 2
        assert await handlers.sign_in_token_exchange(make_context(exchange_activity(), api, state)) is None
        assert api.users.exchange_token.await_count == 2
        assert len(emitted(emitter, "sign_in")) == 2

    @pytest.mark.asyncio
    async def test_expired_persisted_markers_are_pruned_from_conversation_state(self, monkeypatch):
        handlers, _emitter, _flow = make_handlers()
        api = make_api()
        state = make_state()
        clock = {"now": 1_000.0}
        monkeypatch.setattr("microsoft_teams.apps.app_oauth.time", lambda: clock["now"])
        monkeypatch.setattr("microsoft_teams.apps.oauth_state.time", lambda: clock["now"])

        await handlers.sign_in_token_exchange(make_context(exchange_activity("old"), api, state))
        clock["now"] += DEDUP_TTL_SECONDS + 1
        await handlers.sign_in_token_exchange(make_context(exchange_activity("new"), api, state))

        markers = [key for key in state.conversation if key.startswith(EXCHANGE_STATE_KEY_PREFIX)]
        assert markers == [f"{EXCHANGE_STATE_KEY_PREFIX}new"]

    @pytest.mark.asyncio
    async def test_marker_from_the_future_is_treated_as_corrupt(self, monkeypatch):
        """A clock jump backwards must not pin a marker in place forever."""
        handlers, _emitter, _flow = make_handlers()
        api = make_api()
        state = make_state()
        monkeypatch.setattr("microsoft_teams.apps.oauth_state.time", lambda: 1_000.0)
        # A well-formed ISO value, so this exercises the clock-skew guard rather than
        # merely failing to parse.
        state.conversation[f"{EXCHANGE_STATE_KEY_PREFIX}exchange-1"] = iso(1_000.0 + (60 * 60))

        assert await handlers.sign_in_token_exchange(make_context(exchange_activity(), api, state)) is None
        assert api.users.exchange_token.await_count == 1

    @pytest.mark.asyncio
    async def test_in_memory_markers_are_bounded(self):
        """Past the cap the oldest ids are evicted, so the set cannot grow forever."""
        handlers, _emitter, _flow = make_handlers()
        api = make_api()

        for index in range(DEDUP_MAX_ENTRIES + 1):
            await handlers.sign_in_token_exchange(make_context(exchange_activity(f"exchange-{index}"), api))
        assert api.users.exchange_token.await_count == DEDUP_MAX_ENTRIES + 1

        # The newest id is still remembered...
        newest = f"exchange-{DEDUP_MAX_ENTRIES}"
        assert status_of(await handlers.sign_in_token_exchange(make_context(exchange_activity(newest), api))) == 200
        assert api.users.exchange_token.await_count == DEDUP_MAX_ENTRIES + 1

        # ...while the oldest was evicted to keep the set bounded.
        assert await handlers.sign_in_token_exchange(make_context(exchange_activity("exchange-0"), api)) is None
        assert api.users.exchange_token.await_count == DEDUP_MAX_ENTRIES + 2

    @pytest.mark.asyncio
    async def test_expired_in_memory_markers_are_pruned_without_state(self, monkeypatch):
        handlers, _emitter, _flow = make_handlers()
        api = make_api()
        clock = {"now": 1_000.0}
        monkeypatch.setattr("microsoft_teams.apps.app_oauth.time", lambda: clock["now"])

        await handlers.sign_in_token_exchange(make_context(exchange_activity(), api))
        clock["now"] += DEDUP_TTL_SECONDS + 1

        assert await handlers.sign_in_token_exchange(make_context(exchange_activity(), api)) is None
        assert api.users.exchange_token.await_count == 2


class TestOtherSignInCallbacksAreNotDeduplicated:
    @pytest.mark.asyncio
    async def test_verify_state_is_not_deduplicated(self):
        """The verify code is single-use, so repeats are naturally idempotent."""
        handlers, emitter, flow = make_handlers()
        signin_calls: List[str] = []

        @flow.on_signin
        async def on_signin(event):
            signin_calls.append(event.connection_name)

        api = make_api()
        first = make_context(verify_state_activity(), api)
        second = make_context(verify_state_activity(), api)

        assert await handlers.sign_in_verify_state(first) is None
        assert await handlers.sign_in_verify_state(second) is None

        assert api.users.get_token.await_count == 2
        assert len(emitted(emitter, "sign_in")) == 2
        assert signin_calls == [CONNECTION_NAME, CONNECTION_NAME]
        assert first.next.await_count == 1
        assert second.next.await_count == 1

    @pytest.mark.asyncio
    async def test_concurrent_verify_states_are_not_deduplicated(self):
        handlers, emitter, _flow = make_handlers()
        get_token = AsyncMock(side_effect=slow_exchange().side_effect)
        api = make_api(get_token=get_token)
        first = make_context(verify_state_activity(), api)
        second = make_context(verify_state_activity(), api)

        await asyncio.gather(
            handlers.sign_in_verify_state(first),
            handlers.sign_in_verify_state(second),
        )

        assert get_token.await_count == 2
        assert len(emitted(emitter, "sign_in")) == 2

    @pytest.mark.asyncio
    async def test_sign_in_failure_is_not_deduplicated(self):
        """Failure is a single informational notice, not a state-changing operation."""
        handlers, emitter, flow = make_handlers()
        failures: List[str] = []

        @flow.on_signin_failure
        async def on_failure(event):
            failures.append(event.code or "")

        api = make_api()
        first = make_context(failure_activity(), api)
        second = make_context(failure_activity(), api)

        assert await handlers.sign_in_failure(first) is None
        assert await handlers.sign_in_failure(second) is None

        assert len(emitted(emitter, "sign_in_failure")) == 2
        assert failures == ["invokeerror", "invokeerror"]
        assert first.next.await_count == 1
        assert second.next.await_count == 1
