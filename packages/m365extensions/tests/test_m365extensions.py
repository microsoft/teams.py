"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from microsoft_agents.activity import Activity, ActivityTypes
from microsoft_teams.api.auth.caller import CallerIds
from microsoft_teams.m365extensions import is_teams_channel, use_teams_sdk
from microsoft_teams.m365extensions.context import agent_sdk_context
from microsoft_teams.m365extensions.credentials import make_agent_sdk_token_provider
from microsoft_teams.m365extensions.middleware import TeamsMiddleware
from microsoft_teams.m365extensions.token import TeamsToken


class TestIsTeamsChannel:
    """``is_teams_channel`` classifies inbound activities by channel."""

    def test_plain_msteams_channel_is_teams(self):
        assert is_teams_channel(SimpleNamespace(channel_id="msteams")) is True

    def test_msteams_subchannel_is_teams(self):
        # Sub-channels like ``msteams:COPILOT`` must still classify as Teams.
        assert is_teams_channel(SimpleNamespace(channel_id="msteams:COPILOT")) is True

    def test_channel_id_object_with_channel_attribute(self):
        # Agents SDK may surface channel_id as an object exposing ``.channel``.
        channel_id = SimpleNamespace(channel="msteams")
        assert is_teams_channel(SimpleNamespace(channel_id=channel_id)) is True

    def test_non_teams_channel_is_false(self):
        assert is_teams_channel(SimpleNamespace(channel_id="webchat")) is False

    def test_missing_channel_id_is_false(self):
        assert is_teams_channel(SimpleNamespace(channel_id=None)) is False


class TestTeamsToken:
    """``TeamsToken`` projects the fields teams.py consumes off an Activity."""

    def _bot_activity(self):
        return SimpleNamespace(
            recipient=SimpleNamespace(id="bot-app-id", name="MyBot"),
            conversation=SimpleNamespace(tenant_id="tenant-1"),
            service_url="https://smba.example.com/teams/",
        )

    def test_projects_bot_fields_from_activity(self):
        token = TeamsToken.from_activity(self._bot_activity())
        assert token.app_id == "bot-app-id"
        assert token.app_display_name == "MyBot"
        assert token.tenant_id == "tenant-1"

    def test_service_url_trailing_slash_is_stripped(self):
        token = TeamsToken.from_activity(self._bot_activity())
        assert token.service_url == "https://smba.example.com/teams"

    def test_bot_caller_classification(self):
        token = TeamsToken.from_activity(self._bot_activity())
        assert token.from_ == "bot"
        assert token.from_id == f"{CallerIds.BOT}:bot-app-id"

    def test_fresh_token_is_not_expired(self):
        token = TeamsToken.from_activity(self._bot_activity())
        assert token.is_expired() is False
        assert token.expiration is not None

    def test_str_is_tagged_sentinel_not_a_bearer(self):
        token = TeamsToken.from_activity(self._bot_activity())
        assert str(token) == "teams-sdk-synthetic://app/bot-app-id"

    def test_missing_app_id_classifies_as_azure_with_service_url_fallback(self):
        activity = SimpleNamespace(
            recipient=SimpleNamespace(id=""),
            conversation=SimpleNamespace(tenant_id=None),
            service_url="",
        )
        token = TeamsToken.from_activity(activity)
        assert token.app_id == ""
        assert token.from_ == "azure"
        assert token.from_id == CallerIds.AZURE
        # Empty service_url falls back to the Bot Framework default endpoint.
        assert token.service_url == "https://smba.trafficmanager.net/teams"


class TestUseTeamsSdkGuards:
    """``use_teams_sdk`` guards credentials it owns from being overridden."""

    @pytest.mark.parametrize("reserved_kwarg", ["client_id", "tenant_id", "token"])
    def test_reserved_kwargs_raise_before_touching_connection_manager(self, reserved_kwarg):
        # Sentinels: the guard must reject reserved kwargs before it reads
        # anything off app / connection_manager, so plain objects are enough.
        with pytest.raises(TypeError, match=reserved_kwarg):
            use_teams_sdk(object(), object(), **{reserved_kwarg: "override"})


def _teams_activity(activity_type: ActivityTypes = ActivityTypes.message, *, channel_id: str = "msteams") -> Activity:
    """A minimal inbound Activity the middleware can translate and route."""
    kwargs: dict[str, object] = dict(
        type=activity_type,
        id="act-1",
        channel_id=channel_id,
        text="help",
        recipient={"id": "bot-app-id", "name": "MyBot"},
        conversation={"id": "conv-1", "tenant_id": "tenant-1"},
        service_url="https://smba.example.com/teams/",
        from_property={"id": "user-1"},
    )
    if activity_type == ActivityTypes.invoke:
        kwargs["name"] = "task/fetch"
        kwargs["value"] = {"data": {}}
    return Activity(**kwargs)


class _FakeContext:
    """Stands in for an Agents SDK TurnContext across the middleware surface."""

    def __init__(self, activity: Activity) -> None:
        self.activity = activity
        self.turn_state: dict[str, object] = {}
        self.send_activity = AsyncMock()


def _fake_app(*, has_route: bool, plugins: list[object], invoke_response: object = None) -> MagicMock:
    """A teams.py ``App`` double exposing only what ``TeamsMiddleware`` touches."""
    app = MagicMock()
    app.initialize = AsyncMock()
    app.plugins = plugins
    app.router.select_handlers.return_value = ["handler"] if has_route else []
    app.activity_processor.process_activity = AsyncMock(return_value=invoke_response)
    return app


class TestTeamsMiddlewareRouting:
    """``TeamsMiddleware.on_turn`` routes Teams turns and short-circuits the rest."""

    async def test_non_teams_channel_falls_through_untouched(self):
        app = _fake_app(has_route=True, plugins=["p"])
        logic = AsyncMock()

        await TeamsMiddleware(app).on_turn(_FakeContext(_teams_activity(channel_id="webchat")), logic)

        logic.assert_awaited_once()
        # A non-Teams turn must never initialize or invoke the teams.py app.
        app.initialize.assert_not_called()
        app.activity_processor.process_activity.assert_not_called()

    async def test_bypass_predicate_falls_through_after_initialize(self):
        app = _fake_app(has_route=True, plugins=["p"])
        logic = AsyncMock()
        mw = TeamsMiddleware(app, should_bypass_teams=lambda _ctx: True)

        await mw.on_turn(_FakeContext(_teams_activity()), logic)

        logic.assert_awaited_once()
        # initialize runs before the bypass check so proactive sends stay safe...
        app.initialize.assert_awaited_once()
        # ...but the bypassed turn is never handled by teams.py.
        app.activity_processor.process_activity.assert_not_called()

    async def test_no_matching_route_falls_through(self):
        app = _fake_app(has_route=False, plugins=["p"])
        logic = AsyncMock()

        await TeamsMiddleware(app).on_turn(_FakeContext(_teams_activity()), logic)

        logic.assert_awaited_once()
        app.initialize.assert_awaited_once()
        app.activity_processor.process_activity.assert_not_called()

    async def test_matching_route_is_handled_by_teams_and_short_circuits(self):
        app = _fake_app(has_route=True, plugins=["p"])
        logic = AsyncMock()

        await TeamsMiddleware(app).on_turn(_FakeContext(_teams_activity()), logic)

        # A matched Teams route is handled by teams.py, not the host logic.
        logic.assert_not_called()
        app.activity_processor.process_activity.assert_awaited_once()
        # The context var is always reset once the turn completes.
        assert agent_sdk_context.get(None) is None

    async def test_configured_plugins_are_propagated_to_process_activity(self):
        # Regression: process_activity was called with plugins=[], which
        # silently disabled every plugin configured on the embedded App.
        plugins = [object(), object()]
        app = _fake_app(has_route=True, plugins=plugins)

        await TeamsMiddleware(app).on_turn(_FakeContext(_teams_activity()), AsyncMock())

        _, kwargs = app.activity_processor.process_activity.await_args
        assert kwargs["plugins"] is plugins

    async def test_invoke_response_is_propagated_back(self):
        response = SimpleNamespace(status=200, body={"ok": True})
        app = _fake_app(has_route=True, plugins=[], invoke_response=response)
        context = _FakeContext(_teams_activity(ActivityTypes.invoke))

        await TeamsMiddleware(app).on_turn(context, AsyncMock())

        context.send_activity.assert_awaited_once()
        sent: Activity = context.send_activity.await_args.args[0]
        assert sent.type == ActivityTypes.invoke_response
        assert sent.value.status == 200
        assert sent.value.body == {"ok": True}

    async def test_message_turn_does_not_send_invoke_response(self):
        app = _fake_app(has_route=True, plugins=[], invoke_response=SimpleNamespace(status=200, body=None))
        context = _FakeContext(_teams_activity(ActivityTypes.message))

        await TeamsMiddleware(app).on_turn(context, AsyncMock())

        # Only invoke turns carry a response back through the pipeline.
        context.send_activity.assert_not_called()


class TestTokenProviderSelection:
    """The token provider picks a connection based on the active turn identity."""

    def _connection_manager(self, provider: MagicMock) -> MagicMock:
        cm = MagicMock()
        cm.get_default_connection.return_value = provider
        cm.get_token_provider.return_value = provider
        return cm

    async def test_no_active_context_uses_default_connection(self):
        provider = MagicMock()
        provider.get_access_token.return_value = "tok"
        cm = self._connection_manager(provider)

        token = await make_agent_sdk_token_provider(cm)("https://graph.microsoft.com/.default")

        assert token == "tok"
        cm.get_default_connection.assert_called_once()
        cm.get_token_provider.assert_not_called()
        # ".default" is stripped to the resource_url MSAL expects.
        provider.get_access_token.assert_called_once_with(
            "https://graph.microsoft.com", ["https://graph.microsoft.com/.default"]
        )

    async def test_identity_context_selects_matching_token_provider(self):
        provider = MagicMock()
        provider.get_access_token.return_value = "tok"
        cm = self._connection_manager(provider)

        context = MagicMock()
        context.turn_state.get.return_value = "claims-identity"
        ctx_token = agent_sdk_context.set(context)
        try:
            await make_agent_sdk_token_provider(cm)("https://graph.microsoft.com/.default")
        finally:
            agent_sdk_context.reset(ctx_token)

        cm.get_token_provider.assert_called_once_with("claims-identity", "https://graph.microsoft.com")
        cm.get_default_connection.assert_not_called()

    async def test_context_without_identity_uses_default_connection(self):
        provider = MagicMock()
        provider.get_access_token.return_value = "tok"
        cm = self._connection_manager(provider)

        context = MagicMock()
        context.turn_state.get.return_value = None  # no AgentIdentity on this turn
        ctx_token = agent_sdk_context.set(context)
        try:
            await make_agent_sdk_token_provider(cm)("https://graph.microsoft.com/.default")
        finally:
            agent_sdk_context.reset(ctx_token)

        cm.get_default_connection.assert_called_once()
        cm.get_token_provider.assert_not_called()

    async def test_token_provider_lookup_failure_falls_back_to_default(self):
        provider = MagicMock()
        provider.get_access_token.return_value = "tok"
        cm = self._connection_manager(provider)
        cm.get_token_provider.side_effect = RuntimeError("lookup failed")

        context = MagicMock()
        context.turn_state.get.return_value = "claims-identity"
        ctx_token = agent_sdk_context.set(context)
        try:
            token = await make_agent_sdk_token_provider(cm)("https://graph.microsoft.com/.default")
        finally:
            agent_sdk_context.reset(ctx_token)

        assert token == "tok"
        cm.get_default_connection.assert_called_once()

    async def test_awaitable_access_token_is_awaited(self):
        async def _async_token(*_args: object) -> str:
            return "async-tok"

        provider = MagicMock()
        provider.get_access_token.return_value = _async_token()
        cm = self._connection_manager(provider)

        token = await make_agent_sdk_token_provider(cm)("https://graph.microsoft.com/.default")

        assert token == "async-tok"
