"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import dataclasses

import pytest

from microsoft_teams.api.auth.cloud_environment import (
    CHINA,
    PUBLIC,
    US_GOV,
    US_GOV_DOD,
    CloudEnvironment,
    from_name,
    with_overrides,
)


@pytest.mark.unit
class TestCloudEnvironmentPresets:
    def test_public_has_correct_endpoints(self):
        assert PUBLIC.login_endpoint == "https://login.microsoftonline.com"
        assert PUBLIC.login_tenant == "botframework.com"
        assert PUBLIC.bot_scope == "https://api.botframework.com/.default"
        assert PUBLIC.token_service_url == "https://token.botframework.com"
        assert PUBLIC.openid_metadata_url == "https://login.botframework.com/v1/.well-known/openidconfiguration"
        assert PUBLIC.token_issuer == "https://api.botframework.com"
        assert PUBLIC.channel_service == ""
        assert PUBLIC.oauth_redirect_url == "https://token.botframework.com/.auth/web/redirect"

    def test_us_gov_has_correct_endpoints(self):
        assert US_GOV.login_endpoint == "https://login.microsoftonline.us"
        assert US_GOV.login_tenant == "MicrosoftServices.onmicrosoft.us"
        assert US_GOV.bot_scope == "https://api.botframework.us/.default"
        assert US_GOV.token_service_url == "https://tokengcch.botframework.azure.us"
        assert US_GOV.openid_metadata_url == "https://login.botframework.azure.us/v1/.well-known/openidconfiguration"
        assert US_GOV.token_issuer == "https://api.botframework.us"
        assert US_GOV.channel_service == "https://botframework.azure.us"
        assert US_GOV.oauth_redirect_url == "https://tokengcch.botframework.azure.us/.auth/web/redirect"

    def test_us_gov_dod_has_correct_endpoints(self):
        assert US_GOV_DOD.login_endpoint == "https://login.microsoftonline.us"
        assert US_GOV_DOD.token_service_url == "https://apiDoD.botframework.azure.us"
        assert US_GOV_DOD.token_issuer == "https://api.botframework.us"
        assert US_GOV_DOD.channel_service == "https://botframework.azure.us"

    def test_china_has_correct_endpoints(self):
        assert CHINA.login_endpoint == "https://login.partner.microsoftonline.cn"
        assert CHINA.login_tenant == "microsoftservices.partner.onmschina.cn"
        assert CHINA.bot_scope == "https://api.botframework.azure.cn/.default"
        assert CHINA.token_service_url == "https://token.botframework.azure.cn"
        assert CHINA.token_issuer == "https://api.botframework.azure.cn"
        assert CHINA.channel_service == "https://botframework.azure.cn"

    def test_presets_are_frozen(self):
        with pytest.raises(dataclasses.FrozenInstanceError):
            PUBLIC.login_endpoint = "https://modified.example.com"  # type: ignore[misc]


@pytest.mark.unit
class TestFromName:
    @pytest.mark.parametrize(
        "name,expected",
        [
            ("Public", PUBLIC),
            ("public", PUBLIC),
            ("PUBLIC", PUBLIC),
            ("USGov", US_GOV),
            ("usgov", US_GOV),
            ("USGovDoD", US_GOV_DOD),
            ("usgovdod", US_GOV_DOD),
            ("China", CHINA),
            ("china", CHINA),
        ],
    )
    def test_resolves_correctly(self, name: str, expected: CloudEnvironment):
        assert from_name(name) is expected

    @pytest.mark.parametrize("name", ["invalid", "", "Azure"])
    def test_raises_for_unknown_name(self, name: str):
        with pytest.raises(ValueError, match="Unknown cloud environment"):
            from_name(name)


@pytest.mark.unit
class TestWithOverrides:
    def test_returns_same_instance_when_no_overrides(self):
        result = with_overrides(PUBLIC)
        assert result is PUBLIC

    def test_returns_same_instance_when_all_none(self):
        result = with_overrides(PUBLIC, login_endpoint=None, login_tenant=None)
        assert result is PUBLIC

    def test_replaces_single_property(self):
        result = with_overrides(PUBLIC, login_tenant="my-tenant-id")
        assert result is not PUBLIC
        assert result.login_tenant == "my-tenant-id"
        assert result.login_endpoint == PUBLIC.login_endpoint
        assert result.bot_scope == PUBLIC.bot_scope

    def test_replaces_multiple_properties(self):
        result = with_overrides(
            CHINA,
            login_endpoint="https://custom.login.cn",
            login_tenant="custom-tenant",
            token_service_url="https://custom.token.cn",
        )
        assert result.login_endpoint == "https://custom.login.cn"
        assert result.login_tenant == "custom-tenant"
        assert result.token_service_url == "https://custom.token.cn"
        assert result.bot_scope == CHINA.bot_scope

    def test_replaces_all_properties(self):
        result = with_overrides(
            PUBLIC,
            login_endpoint="a",
            login_tenant="b",
            bot_scope="c",
            token_service_url="d",
            openid_metadata_url="e",
            token_issuer="f",
            channel_service="g",
            oauth_redirect_url="h",
        )
        assert result.login_endpoint == "a"
        assert result.login_tenant == "b"
        assert result.bot_scope == "c"
        assert result.token_service_url == "d"
        assert result.openid_metadata_url == "e"
        assert result.token_issuer == "f"
        assert result.channel_service == "g"
        assert result.oauth_redirect_url == "h"

    def test_result_is_frozen(self):
        result = with_overrides(PUBLIC, login_tenant="test")
        with pytest.raises(dataclasses.FrozenInstanceError):
            result.login_tenant = "modified"  # type: ignore[misc]
