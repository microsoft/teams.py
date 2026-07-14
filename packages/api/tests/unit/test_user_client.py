"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

# pyright: basic

import pytest
from microsoft_teams.api import (
    ApiClient,
    ApiClientSettings,
    ExchangeUserTokenParams,
    GetUserAADTokenParams,
    GetUserTokenParams,
    GetUserTokenStatusParams,
    SignOutUserParams,
    TokenExchangeRequest,
    UserClient,
)


@pytest.mark.unit
class TestUserClient:
    @pytest.mark.asyncio
    async def test_user_token_get(self, mock_http_client):
        client = UserClient(mock_http_client)

        params = GetUserTokenParams(
            user_id="test_user_id",
            connection_name="test_connection",
            channel_id="test_channel_id",
            code="auth_code_123",
        )

        response = await client.token.get(params)

        assert response.token is not None
        assert response.token == "mock_access_token_123"
        assert response.connection_name == "test_connection"

    @pytest.mark.asyncio
    async def test_user_token_get_uses_auth_provider_for_bot_token(self, mock_http_client):
        calls = []

        class TestAuthProvider:
            def token(self, *, scope=None, agentic_identity=None):
                calls.append((scope, agentic_identity))
                return "bot-token"

        client = ApiClient("https://test.service.url", mock_http_client, auth_provider=TestAuthProvider()).users
        params = GetUserTokenParams(
            user_id="test_user_id",
            connection_name="test_connection",
            channel_id="test_channel_id",
        )

        await client.token.get(params)

        assert calls == [(None, None)]

    @pytest.mark.asyncio
    async def test_user_token_get_aad(self, mock_http_client):
        client = UserClient(mock_http_client)

        params = GetUserAADTokenParams(
            user_id="test_user_id",
            connection_name="test_connection",
            resource_urls=["https://graph.microsoft.com", "https://api.botframework.com"],
            channel_id="test_channel_id",
        )

        response = await client.token.get_aad(params)

        assert response.get("https://graph.microsoft.com") is not None
        assert response.get("https://api.botframework.com") is not None

    @pytest.mark.asyncio
    async def test_user_token_get_status(self, mock_http_client):
        client = UserClient(mock_http_client)

        params = GetUserTokenStatusParams(
            user_id="test_user_id",
            channel_id="test_channel_id",
            include_filter="*",
        )

        response = await client.token.get_status(params)

        assert len(response) > 0
        for item in response:
            assert item.connection_name == "test_connection"
            assert item.has_token is True

    @pytest.mark.asyncio
    async def test_user_token_sign_out(self, mock_http_client):
        client = UserClient(mock_http_client)

        params = SignOutUserParams(
            user_id="test_user_id",
            connection_name="test_connection",
            channel_id="test_channel_id",
        )

        # Should not raise an exception
        result = await client.token.sign_out(params)
        assert result is None or result is True

    @pytest.mark.asyncio
    async def test_user_token_exchange(self, mock_http_client):
        client = UserClient(mock_http_client)

        exchange_request = TokenExchangeRequest(
            uri="https://test.resource.com",
            token="exchange_token_123",
        )

        params = ExchangeUserTokenParams(
            user_id="test_user_id",
            connection_name="test_connection",
            channel_id="test_channel_id",
            exchange_request=exchange_request,
        )

        response = await client.token.exchange(params)

        assert response.token is not None
        assert response.token == "mock_exchanged_token_123"
        assert response.connection_name == "test_connection"


@pytest.mark.unit
class TestUserClientHttpClientSharing:
    def test_http_client_sharing(self, mock_http_client):
        client = UserClient(mock_http_client)

        assert client.token.http == mock_http_client

    def test_http_client_update_propagates(self, mock_http_client):
        from microsoft_teams.common.http import Client, ClientOptions

        client = UserClient(mock_http_client)
        new_http_client = Client(ClientOptions(base_url="https://new.api.com"))

        # Update the HTTP client
        client.http = new_http_client

        assert client.token.http == new_http_client


@pytest.mark.unit
class TestUserClientSovereignCloud:
    def test_user_token_client_uses_cloud_token_service_url(self):
        from microsoft_teams.api.auth.cloud_environment import US_GOV

        client = UserClient(cloud=US_GOV)
        assert client.token._api_client_settings.oauth_url == US_GOV.token_service_url


@pytest.mark.unit
class TestUserClientRegionalEndpoints:
    @pytest.mark.asyncio
    async def test_user_token_get_with_regional_endpoint(self, mock_http_client):
        regional_settings = ApiClientSettings(oauth_url="https://europe.token.botframework.com")
        client = UserClient(mock_http_client, regional_settings)

        params = GetUserTokenParams(
            user_id="test_user_id",
            connection_name="test_connection",
            channel_id="test_channel_id",
            code="auth_code_123",
        )

        response = await client.token.get(params)

        assert response.token is not None
        assert response.token == "mock_access_token_123"
        assert response.connection_name == "test_connection"

    @pytest.mark.asyncio
    async def test_user_token_get_aad_with_regional_endpoint(self, mock_http_client):
        regional_settings = ApiClientSettings(oauth_url="https://europe.token.botframework.com")
        client = UserClient(mock_http_client, regional_settings)

        params = GetUserAADTokenParams(
            user_id="test_user_id",
            connection_name="test_connection",
            resource_urls=["https://graph.microsoft.com"],
            channel_id="test_channel_id",
        )

        response = await client.token.get_aad(params)

        assert response.get("https://graph.microsoft.com") is not None

    @pytest.mark.asyncio
    async def test_user_token_get_status_with_regional_endpoint(self, mock_http_client):
        regional_settings = ApiClientSettings(oauth_url="https://europe.token.botframework.com")
        client = UserClient(mock_http_client, regional_settings)

        params = GetUserTokenStatusParams(
            user_id="test_user_id",
            channel_id="test_channel_id",
            include_filter="*",
        )

        response = await client.token.get_status(params)

        assert len(response) > 0
        for item in response:
            assert item.connection_name == "test_connection"
            assert item.has_token is True

    @pytest.mark.asyncio
    async def test_user_token_sign_out_with_regional_endpoint(self, mock_http_client):
        regional_settings = ApiClientSettings(oauth_url="https://europe.token.botframework.com")
        client = UserClient(mock_http_client, regional_settings)

        params = SignOutUserParams(
            user_id="test_user_id",
            connection_name="test_connection",
            channel_id="test_channel_id",
        )

        result = await client.token.sign_out(params)
        assert result is None or result is True

    @pytest.mark.asyncio
    async def test_user_token_exchange_with_regional_endpoint(self, mock_http_client):
        regional_settings = ApiClientSettings(oauth_url="https://europe.token.botframework.com")
        client = UserClient(mock_http_client, regional_settings)

        exchange_request = TokenExchangeRequest(
            uri="https://test.resource.com",
            token="exchange_token_123",
        )

        params = ExchangeUserTokenParams(
            user_id="test_user_id",
            connection_name="test_connection",
            channel_id="test_channel_id",
            exchange_request=exchange_request,
        )

        response = await client.token.exchange(params)

        assert response.token is not None
        assert response.token == "mock_exchanged_token_123"
        assert response.connection_name == "test_connection"


@pytest.mark.unit
class TestUserClientFlattened:
    """Unit tests for the flattened UserClient methods (users.get_token, etc.)."""

    @pytest.mark.asyncio
    async def test_get_token(self, mock_http_client):
        client = UserClient(mock_http_client)

        params = GetUserTokenParams(
            user_id="test_user_id",
            connection_name="test_connection",
            channel_id="test_channel_id",
            code="auth_code_123",
        )

        response = await client.get_token(params)

        assert response.token == "mock_access_token_123"
        assert response.connection_name == "test_connection"

    @pytest.mark.asyncio
    async def test_get_aad_tokens(self, mock_http_client):
        client = UserClient(mock_http_client)

        params = GetUserAADTokenParams(
            user_id="test_user_id",
            connection_name="test_connection",
            resource_urls=["https://graph.microsoft.com", "https://api.botframework.com"],
            channel_id="test_channel_id",
        )

        response = await client.get_aad_tokens(params)

        assert response.get("https://graph.microsoft.com") is not None
        assert response.get("https://api.botframework.com") is not None

    @pytest.mark.asyncio
    async def test_get_token_status(self, mock_http_client):
        client = UserClient(mock_http_client)

        params = GetUserTokenStatusParams(
            user_id="test_user_id",
            channel_id="test_channel_id",
            include_filter="*",
        )

        response = await client.get_token_status(params)

        assert len(response) > 0
        assert response[0].connection_name == "test_connection"
        assert response[0].has_token is True

    @pytest.mark.asyncio
    async def test_sign_out(self, mock_http_client):
        client = UserClient(mock_http_client)

        params = SignOutUserParams(
            user_id="test_user_id",
            connection_name="test_connection",
            channel_id="test_channel_id",
        )

        result = await client.sign_out(params)
        assert result is None

    @pytest.mark.asyncio
    async def test_exchange_token(self, mock_http_client):
        client = UserClient(mock_http_client)

        params = ExchangeUserTokenParams(
            user_id="test_user_id",
            connection_name="test_connection",
            channel_id="test_channel_id",
            exchange_request=TokenExchangeRequest(
                uri="https://test.resource.com",
                token="exchange_token_123",
            ),
        )

        response = await client.exchange_token(params)

        assert response.token == "mock_exchanged_token_123"
        assert response.connection_name == "test_connection"

    def test_deprecated_token_accessor_warns(self, mock_http_client):
        """The deprecated `token` accessor still works but emits a DeprecationWarning."""
        client = UserClient(mock_http_client)

        with pytest.warns(DeprecationWarning):
            token_client = client.token

        assert token_client.http == mock_http_client
