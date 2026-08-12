"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from types import SimpleNamespace

import pytest
from microsoft_teams.api.auth.caller import CallerIds
from microsoft_teams.m365extensions import is_teams_channel, use_teams_sdk
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
