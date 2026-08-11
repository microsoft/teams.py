"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

# pyright: basic

from unittest.mock import AsyncMock, MagicMock

import pytest
from microsoft_teams.apps import App, OAuthFlow, OAuthFlowRegistry
from microsoft_teams.apps.routing import SignInOptions


class TestOAuthFlowHandlers:
    """Handler registration on an OAuthFlow."""

    def test_on_signin_registers_and_returns_handler(self) -> None:
        flow = OAuthFlow("graph")

        async def handler(event) -> None:
            pass

        returned = flow.on_signin(handler)

        assert returned is handler
        assert flow._on_signin == [handler]

    def test_on_signin_failure_registers_and_returns_handler(self) -> None:
        flow = OAuthFlow("graph")

        async def handler(event) -> None:
            pass

        returned = flow.on_signin_failure(handler)

        assert returned is handler
        assert flow._on_signin_failure == [handler]

    def test_multiple_handlers_preserve_order(self) -> None:
        flow = OAuthFlow("graph")

        async def first(event) -> None:
            pass

        async def second(event) -> None:
            pass

        flow.on_signin(first)
        flow.on_signin(second)

        assert flow._on_signin == [first, second]


class TestOAuthFlowOperations:
    """sign_in / sign_out / get_token / is_signed_in delegate to the context."""

    @pytest.mark.asyncio
    async def test_sign_in_forces_flow_connection_name(self) -> None:
        flow = OAuthFlow("graph")
        ctx = MagicMock()
        ctx.sign_in = AsyncMock(return_value="tok")

        result = await flow.sign_in(ctx)

        assert result == "tok"
        ctx.sign_in.assert_awaited_once()
        passed = ctx.sign_in.call_args[0][0]
        assert isinstance(passed, SignInOptions)
        assert passed.connection_name == "graph"

    @pytest.mark.asyncio
    async def test_sign_in_keeps_caller_card_text_but_overrides_connection(self) -> None:
        flow = OAuthFlow("graph")
        ctx = MagicMock()
        ctx.sign_in = AsyncMock(return_value=None)

        custom = SignInOptions(oauth_card_text="Custom text", connection_name="wrong")
        await flow.sign_in(ctx, custom)

        passed = ctx.sign_in.call_args[0][0]
        assert passed.oauth_card_text == "Custom text"
        assert passed.connection_name == "graph"

    @pytest.mark.asyncio
    async def test_sign_in_uses_flow_defaults(self) -> None:
        flow = OAuthFlow("graph", oauth_card_text="Sign in here", sign_in_button_text="Go")
        ctx = MagicMock()
        ctx.sign_in = AsyncMock(return_value=None)

        await flow.sign_in(ctx)

        passed = ctx.sign_in.call_args[0][0]
        assert passed.oauth_card_text == "Sign in here"
        assert passed.sign_in_button_text == "Go"
        assert passed.connection_name == "graph"

    @pytest.mark.asyncio
    async def test_sign_out_targets_flow_connection(self) -> None:
        flow = OAuthFlow("graph")
        ctx = MagicMock()
        ctx.sign_out = AsyncMock(return_value=None)

        await flow.sign_out(ctx)

        ctx.sign_out.assert_awaited_once_with(connection_name="graph")

    @pytest.mark.asyncio
    async def test_get_token_returns_ctx_token(self) -> None:
        flow = OAuthFlow("graph")
        ctx = MagicMock()
        ctx.get_user_token = AsyncMock(return_value="tok")

        result = await flow.get_token(ctx)

        assert result == "tok"
        ctx.get_user_token.assert_awaited_once_with(connection_name="graph")

    @pytest.mark.asyncio
    async def test_is_signed_in_true_when_token_present(self) -> None:
        flow = OAuthFlow("graph")
        ctx = MagicMock()
        ctx.get_user_token = AsyncMock(return_value="tok")

        assert await flow.is_signed_in(ctx) is True

    @pytest.mark.asyncio
    async def test_is_signed_in_false_when_no_token(self) -> None:
        flow = OAuthFlow("graph")
        ctx = MagicMock()
        ctx.get_user_token = AsyncMock(return_value=None)

        assert await flow.is_signed_in(ctx) is False


class TestOAuthFlowRegistry:
    """The case-insensitive, insertion-ordered flow registry."""

    def test_add_and_get_case_insensitive(self) -> None:
        registry = OAuthFlowRegistry()
        flow = OAuthFlow("Graph")

        registry.add(flow)

        assert registry["graph"] is flow
        assert registry["GRAPH"] is flow
        assert registry["Graph"] is flow

    def test_add_returns_flow(self) -> None:
        registry = OAuthFlowRegistry()
        flow = OAuthFlow("graph")

        assert registry.add(flow) is flow

    def test_add_duplicate_raises_value_error(self) -> None:
        registry = OAuthFlowRegistry()
        registry.add(OAuthFlow("Graph"))

        with pytest.raises(ValueError, match="already"):
            registry.add(OAuthFlow("graph"))

    def test_contains_and_get(self) -> None:
        registry = OAuthFlowRegistry()
        flow = OAuthFlow("graph")
        registry.add(flow)

        assert "GRAPH" in registry
        assert registry.get("graph") is flow
        assert registry.get("missing") is None

    def test_len_and_iter_preserve_insertion_order(self) -> None:
        registry = OAuthFlowRegistry()
        registry.add(OAuthFlow("Graph"))
        registry.add(OAuthFlow("GitHub"))

        assert len(registry) == 2
        assert list(registry) == ["graph", "github"]
        assert [f.connection_name for f in registry.values()] == ["Graph", "GitHub"]

    def test_empty_registry_is_falsy(self) -> None:
        assert not OAuthFlowRegistry()


class TestAppOAuthFlowIntegration:
    """app.add_oauth_flow / app.get_oauth_flow."""

    @pytest.fixture
    def app(self) -> App:
        return App(storage=MagicMock(), client_id="test-client-id", client_secret="test-secret")

    def test_add_oauth_flow_returns_registered_flow(self, app: App) -> None:
        flow = app.add_oauth_flow("graph", oauth_card_text="Hi", sign_in_button_text="Go")

        assert isinstance(flow, OAuthFlow)
        assert flow.connection_name == "graph"
        assert app.get_oauth_flow("graph") is flow

    def test_get_oauth_flow_is_case_insensitive(self, app: App) -> None:
        flow = app.add_oauth_flow("Graph")

        assert app.get_oauth_flow("graph") is flow
        assert app.get_oauth_flow("GRAPH") is flow

    def test_add_duplicate_flow_raises(self, app: App) -> None:
        app.add_oauth_flow("graph")

        with pytest.raises(ValueError, match="already"):
            app.add_oauth_flow("Graph")

    def test_get_missing_flow_raises_with_registered_names(self, app: App) -> None:
        app.add_oauth_flow("graph")
        app.add_oauth_flow("github")

        with pytest.raises(ValueError, match="graph, github"):
            app.get_oauth_flow("missing")

    def test_get_missing_flow_on_empty_registry_lists_none(self, app: App) -> None:
        with pytest.raises(ValueError, match="<none>"):
            app.get_oauth_flow("missing")
