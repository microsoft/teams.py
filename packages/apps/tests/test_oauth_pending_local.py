"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

# pyright: basic

from typing import Any, Iterator
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import HTTPStatusError, Request, Response
from microsoft_teams.api import (
    Account,
    ConversationAccount,
    ConversationReference,
    MessageActivity,
    MessageActivityInput,
    SentActivity,
)
from microsoft_teams.api.auth.cloud_environment import PUBLIC
from microsoft_teams.apps import OAuthFlow, OAuthFlowRegistry
from microsoft_teams.apps import oauth_pending_local as local
from microsoft_teams.apps.oauth_state import (
    clear_pending_oauth_sign_in,
    get_pending_oauth_sign_ins,
    record_pending_oauth_sign_in,
)
from microsoft_teams.apps.routing.activity_context import ActivityContext


@pytest.fixture(autouse=True)
def _isolate_store() -> Iterator[None]:
    """The store is process-wide, so each test starts and ends from empty."""
    local._entries.clear()
    yield
    local._entries.clear()


def _sign_in_context(conversation_id: str = "conv-1", user_id: str = "user-1") -> ActivityContext[Any]:
    """A context with state disabled, wired well enough to send an OAuth card."""
    activity = MessageActivity(
        id="activity-id",
        channel_id="msteams",
        from_=Account(id=user_id),
        recipient=Account(id="bot-id"),
        conversation=ConversationAccount(id=conversation_id, is_group=False),
    )
    api = MagicMock()
    api.clone.return_value = api
    api.users.get_token = AsyncMock(
        side_effect=HTTPStatusError(
            "HTTP 404",
            request=Request("GET", "https://token.example"),
            response=Response(404, request=Request("GET", "https://token.example")),
        )
    )
    resource = MagicMock()
    resource.token_exchange_resource = None
    resource.token_post_resource = None
    resource.sign_in_link = "https://login.example.com"
    api._bots.sign_in.get_resource = AsyncMock(return_value=resource)
    api.conversations.create_activity = AsyncMock(
        return_value=SentActivity(id="sent", activity_params=MessageActivityInput(text="sent"))
    )

    ctx = ActivityContext(
        activity=activity,
        app_id="app-id",
        storage=MagicMock(),
        api=api,
        user_token=None,
        conversation_ref=ConversationReference(
            bot=Account(id="bot-id"),
            conversation=ConversationAccount(id=conversation_id),
            channel_id="msteams",
            service_url="https://service.example",
        ),
        is_signed_in=False,
        connection_name="test-connection",
        app_token=MagicMock(),
        cloud=PUBLIC,
    )
    # State disabled: this is the whole point of the fallback.
    assert ctx.state is None
    return ctx


class TestStateDisabledAttribution:
    """With state off, a sign-in and its callback still find each other."""

    @pytest.mark.asyncio
    async def test_sign_in_records_a_hint_that_the_callback_can_read(self) -> None:
        """Red-green: without the fallback this returns [] and the callback
        falls back to probing every connection."""
        ctx = _sign_in_context()

        await ctx.sign_in()

        hints = get_pending_oauth_sign_ins(None, "conv-1", "user-1")
        assert [hint.connection_name for hint in hints] == ["test-connection"]

    @pytest.mark.asyncio
    async def test_the_registry_resolves_the_hint_to_the_right_flow(self) -> None:
        """The end the callback actually uses: hint -> registered flow."""
        registry = OAuthFlowRegistry()
        mail = registry.add(OAuthFlow("graphmail"))
        registry.add(OAuthFlow("graphuser"))
        record_pending_oauth_sign_in(None, "graphmail", sso_offered=False, conversation_id="c", user_id="u")

        ctx = MagicMock()
        ctx.state = None
        ctx.activity.conversation.id = "c"
        ctx.activity.from_.id = "u"

        assert registry._pending_flows(ctx) == [mail]

    def test_another_conversation_sees_nothing(self) -> None:
        """Hints are scoped, so one chat cannot route another chat's callback."""
        record_pending_oauth_sign_in(None, "graph", sso_offered=False, conversation_id="c1", user_id="u")

        assert get_pending_oauth_sign_ins(None, "c2", "u") == []

    def test_another_user_in_the_same_conversation_sees_nothing(self) -> None:
        """Two people signing in to the same connection stay independent."""
        record_pending_oauth_sign_in(None, "graph", sso_offered=False, conversation_id="c", user_id="u1")

        assert get_pending_oauth_sign_ins(None, "c", "u2") == []

    def test_a_different_process_finds_nothing_and_falls_back(self) -> None:
        """The store is process-local by design; another instance sees empty.

        Emptiness is the contract: the caller then probes every candidate, which
        is the pre-existing behaviour and still correct, only slower.
        """
        assert get_pending_oauth_sign_ins(None, "c", "u") == []

    def test_missing_identifiers_record_nothing(self) -> None:
        """Without a scope there is no safe key, so nothing is stored."""
        record_pending_oauth_sign_in(None, "graph", sso_offered=False, conversation_id=None, user_id="u")
        record_pending_oauth_sign_in(None, "graph", sso_offered=False, conversation_id="c", user_id=None)

        assert dict(local._entries) == {}

    def test_state_when_available_is_used_instead_of_the_store(self) -> None:
        """The fallback must never shadow real state."""
        state = MagicMock()
        state.user = {}
        record_pending_oauth_sign_in(state, "graph", sso_offered=False, conversation_id="c", user_id="u")

        assert dict(local._entries) == {}
        assert any(key.startswith("__oauth:pending:") for key in state.user)


class TestProcessLocalStoreMechanics:
    """TTL, bounds, and the small operations built on top of the store."""

    def test_hints_are_newest_first(self) -> None:
        record_pending_oauth_sign_in(None, "first", sso_offered=False, conversation_id="c", user_id="u")
        record_pending_oauth_sign_in(None, "second", sso_offered=False, conversation_id="c", user_id="u")

        names = [hint.connection_name for hint in get_pending_oauth_sign_ins(None, "c", "u")]
        assert names[0] == "second"

    def test_re_signing_in_replaces_the_earlier_attempt(self) -> None:
        """One connection has at most one pending attempt."""
        record_pending_oauth_sign_in(None, "graph", sso_offered=True, conversation_id="c", user_id="u")
        record_pending_oauth_sign_in(None, "GRAPH", sso_offered=False, conversation_id="c", user_id="u")

        hints = get_pending_oauth_sign_ins(None, "c", "u")
        assert len(hints) == 1
        assert hints[0].sso_offered is False

    def test_expired_hints_are_dropped(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A five-minute-old sign-in is no longer a plausible attribution."""
        clock = [1000.0]
        monkeypatch.setattr(local, "time", lambda: clock[0])
        record_pending_oauth_sign_in(None, "graph", sso_offered=False, conversation_id="c", user_id="u")

        clock[0] += local._TTL_SECONDS - 1
        assert len(get_pending_oauth_sign_ins(None, "c", "u")) == 1

        clock[0] += 2
        assert get_pending_oauth_sign_ins(None, "c", "u") == []

    def test_the_store_is_capped(self) -> None:
        """A long-running process cannot grow this without bound."""
        for index in range(local._MAX_ENTRIES + 50):
            record_pending_oauth_sign_in(None, "graph", sso_offered=False, conversation_id=f"c{index}", user_id="u")

        assert len(local._entries) == local._MAX_ENTRIES

    def test_eviction_drops_the_oldest_first(self) -> None:
        """Deterministic: insertion order is age order, so the front goes."""
        for index in range(local._MAX_ENTRIES + 1):
            record_pending_oauth_sign_in(None, "graph", sso_offered=False, conversation_id=f"c{index}", user_id="u")

        assert get_pending_oauth_sign_ins(None, "c0", "u") == []
        assert len(get_pending_oauth_sign_ins(None, f"c{local._MAX_ENTRIES}", "u")) == 1

    def test_clearing_one_connection_leaves_the_others(self) -> None:
        record_pending_oauth_sign_in(None, "graph", sso_offered=False, conversation_id="c", user_id="u")
        record_pending_oauth_sign_in(None, "mail", sso_offered=False, conversation_id="c", user_id="u")

        clear_pending_oauth_sign_in(None, "GRAPH", "c", "u")

        assert [hint.connection_name for hint in get_pending_oauth_sign_ins(None, "c", "u")] == ["mail"]

    def test_clearing_without_a_name_clears_the_whole_scope(self) -> None:
        record_pending_oauth_sign_in(None, "graph", sso_offered=False, conversation_id="c", user_id="u")
        record_pending_oauth_sign_in(None, "mail", sso_offered=False, conversation_id="c", user_id="u")

        clear_pending_oauth_sign_in(None, None, "c", "u")

        assert get_pending_oauth_sign_ins(None, "c", "u") == []

    def test_clearing_retires_an_sso_hint_entirely(self) -> None:
        """The whole hint goes, SSO marker included, so nothing survives to re-route."""
        record_pending_oauth_sign_in(None, "graph", sso_offered=True, conversation_id="c", user_id="u")

        clear_pending_oauth_sign_in(None, "GRAPH", "c", "u")

        assert get_pending_oauth_sign_ins(None, "c", "u") == []

    def test_replace_restores_the_original_timestamps(self) -> None:
        """Rollback puts back what was there, not a fresh set of hints."""
        record_pending_oauth_sign_in(None, "graph", sso_offered=True, conversation_id="c", user_id="u")
        snapshot = get_pending_oauth_sign_ins(None, "c", "u")
        clear_pending_oauth_sign_in(None, None, "c", "u")

        local.replace("c", "u", [(h.connection_name, h.created_at, h.sso_offered) for h in snapshot])

        assert get_pending_oauth_sign_ins(None, "c", "u") == snapshot

    def test_blank_connection_names_are_not_stored(self) -> None:
        record_pending_oauth_sign_in(None, "   ", sso_offered=False, conversation_id="c", user_id="u")

        assert dict(local._entries) == {}
