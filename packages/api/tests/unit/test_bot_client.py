"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

import pytest
from microsoft_teams.api import (
    ApiClient,
    ApiClientSettings,
    BotClient,
    GetBotSignInResourceParams,
    GetBotSignInUrlParams,
)
from microsoft_teams.api.auth.credentials import TokenCredentials
from microsoft_teams.common.http import Client, ClientOptions


@pytest.mark.unit
class TestBotClient:
    @pytest.mark.asyncio
    async def test_bot_token_get_with_client_credentials(self, mock_http_client, mock_client_credentials):
        client = BotClient(mock_http_client)
        response = await client.token.get(mock_client_credentials)
        assert response.token_type == "Bearer"
        assert response.access_token is not None
        assert response.expires_in > 0

    @pytest.mark.asyncio
    async def test_bot_token_get_with_token_credentials(self, mock_http_client, mock_token_credentials):
        client = BotClient(mock_http_client)
        response = await client.token.get(mock_token_credentials)
        assert response.token_type == "Bearer"
        assert response.access_token is not None
        assert response.expires_in == -1

    @pytest.mark.asyncio
    async def test_bot_token_get_graph_with_client_credentials(self, mock_http_client, mock_client_credentials):
        client = BotClient(mock_http_client)
        response = await client.token.get_graph(mock_client_credentials)
        assert response.token_type == "Bearer"
        assert response.access_token is not None
        assert response.expires_in > 0

    @pytest.mark.asyncio
    async def test_bot_token_get_graph_with_token_credentials(self, mock_http_client, mock_token_credentials):
        client = BotClient(mock_http_client)
        response = await client.token.get_graph(mock_token_credentials)
        assert response.token_type == "Bearer"
        assert response.access_token is not None
        assert response.expires_in == -1

    @pytest.mark.asyncio
    async def test_bot_token_get_with_uninspectable_token_provider_signature(self, mock_http_client):
        from unittest.mock import patch

        calls = []

        def token_provider(scope, tenant_id):
            calls.append((scope, tenant_id))
            return "token"

        credentials = TokenCredentials(client_id="client-id", tenant_id="tenant-id", token=token_provider)
        client = BotClient(mock_http_client)

        with patch("inspect.signature", side_effect=ValueError("no signature")):
            response = await client.token.get(credentials)

        assert response.access_token == "token"
        assert calls == [("https://api.botframework.com/.default", "tenant-id")]

    @pytest.mark.asyncio
    async def test_bot_token_get_with_positional_agentic_user_provider(self, mock_http_client):
        calls = []

        def token_provider(scope, tenant_id, agentic_user):
            calls.append((scope, tenant_id, agentic_user))
            return "token"

        credentials = TokenCredentials(client_id="client-id", tenant_id="tenant-id", token=token_provider)
        client = BotClient(mock_http_client)

        response = await client.token.get(credentials)

        assert response.access_token == "token"
        assert calls == [("https://api.botframework.com/.default", "tenant-id", None)]

    @pytest.mark.asyncio
    async def test_bot_token_get_with_optional_third_argument_uses_default(self, mock_http_client):
        calls = []

        def token_provider(scope, tenant_id, timeout=30):
            calls.append((scope, tenant_id, timeout))
            return "token"

        credentials = TokenCredentials(client_id="client-id", tenant_id="tenant-id", token=token_provider)
        client = BotClient(mock_http_client)

        response = await client.token.get(credentials)

        assert response.access_token == "token"
        assert calls == [("https://api.botframework.com/.default", "tenant-id", 30)]

    @pytest.mark.asyncio
    async def test_bot_sign_in_get_url(self, mock_http_client):
        client = BotClient(mock_http_client)
        params = GetBotSignInUrlParams(
            state="test_state",
            code_challenge="test_challenge",
        )
        url = await client.sign_in.get_url(params)
        assert "mock-signin.url" in url

    @pytest.mark.asyncio
    async def test_bot_sign_in_get_resource(self, mock_http_client):
        client = BotClient(mock_http_client)
        params = GetBotSignInResourceParams(
            state="test_state",
            code_challenge="test_challenge",
        )
        response = await client.sign_in.get_resource(params)
        assert response.sign_in_link is not None
        assert response.sign_in_link.startswith("http")
        assert response.token_exchange_resource is not None

    @pytest.mark.asyncio
    async def test_bot_sign_in_uses_auth_provider_for_bot_token(self, request_capture):
        calls = []

        class TestAuthProvider:
            def token(self, *, scope=None, agentic_user=None):
                calls.append((scope, agentic_user))
                return "bot-token"

        client = ApiClient("https://test.service.url", request_capture, auth_provider=TestAuthProvider())
        params = GetBotSignInResourceParams(state="test_state", code_challenge="test_challenge")

        await client.bots.sign_in.get_resource(params)

        assert calls == [(None, None)]
        request = request_capture._capture.last_request
        assert request.headers["authorization"] == "Bearer bot-token"


@pytest.mark.unit
class TestBotClientHttpClientSharing:
    def test_http_client_sharing(self, mock_http_client):
        client = BotClient(mock_http_client)
        assert client.token.http == mock_http_client
        assert client.sign_in.http == mock_http_client

    def test_http_client_update_propagates(self, mock_http_client):
        client = BotClient(mock_http_client)
        new_http_client = Client(ClientOptions(base_url="https://new.api.com"))
        client.http = new_http_client
        assert client.token.http == new_http_client
        assert client.sign_in.http == new_http_client


@pytest.mark.unit
class TestBotClientRegionalEndpoints:
    @pytest.mark.asyncio
    async def test_bot_sign_in_get_resource_with_regional_endpoint(self, mock_http_client):
        regional_settings = ApiClientSettings(oauth_url="https://europe.token.botframework.com")
        client = BotClient(mock_http_client, regional_settings)
        params = GetBotSignInResourceParams(
            state="test_state",
            code_challenge="test_challenge",
        )
        response = await client.sign_in.get_resource(params)
        assert response.sign_in_link is not None
        assert response.sign_in_link.startswith("http")


@pytest.mark.unit
class TestBotClientSovereignCloud:
    def test_bot_token_client_receives_cloud(self):
        from microsoft_teams.api.auth.cloud_environment import US_GOV

        client = BotClient(cloud=US_GOV)
        assert client.token._cloud is US_GOV
        assert client.token._cloud.bot_scope == "https://api.botframework.us/.default"
        assert client.token._cloud.login_endpoint == "https://login.microsoftonline.us"

    def test_bot_sign_in_client_uses_cloud_token_service_url(self):
        from microsoft_teams.api.auth.cloud_environment import US_GOV

        client = BotClient(cloud=US_GOV)
        assert client.sign_in._api_client_settings.oauth_url == US_GOV.token_service_url

    def test_bot_token_client_defaults_to_public(self):
        from microsoft_teams.api.auth.cloud_environment import PUBLIC

        client = BotClient()
        assert client.token._cloud is PUBLIC

    def test_api_client_passes_cloud_to_bot_client(self):
        from microsoft_teams.api import ApiClient
        from microsoft_teams.api.auth.cloud_environment import US_GOV

        api = ApiClient("https://example.com", cloud=US_GOV)
        assert api.bots.token._cloud is US_GOV
