"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

import pytest
from microsoft_teams.api import ApiClientSettings, BotClient, GetBotSignInResourceParams, GetBotSignInUrlParams
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
