"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

from unittest.mock import AsyncMock, patch

import pytest
from microsoft_teams.api.clients import ApiClient, ReactionClient
from microsoft_teams.common.http import Client, ClientOptions


@pytest.mark.unit
class TestApiClientReactionsProperty:
    """Tests for the reactions property on ApiClient."""

    def test_reactions_first_access_creates_reaction_client(self, mock_http_client):
        """Test that accessing reactions for the first time creates a ReactionClient."""
        client = ApiClient("https://mock.service.url", mock_http_client)
        assert client._reactions is None

        reactions = client.reactions

        assert reactions is not None
        assert isinstance(reactions, ReactionClient)

    def test_reactions_second_access_returns_cached_client(self, mock_http_client):
        """Test that the reactions property returns the same instance on subsequent accesses."""
        client = ApiClient("https://mock.service.url", mock_http_client)
        first = client.reactions
        second = client.reactions
        assert first is second

    def test_http_setter_updates_all_sub_clients(self, mock_http_client):
        """Test that setting http propagates the new client to all sub-clients."""
        client = ApiClient("https://mock.service.url", mock_http_client)
        new_http = Client(ClientOptions(base_url="https://new.service.url"))

        client.http = new_http

        assert client._http is new_http
        assert client._bots.http is new_http
        assert client.conversations.http is new_http
        assert client.users.http is new_http
        assert client.teams.http is new_http
        assert client.meetings.http is new_http

    def test_http_setter_without_reactions_does_not_error(self, mock_http_client):
        """Test that setting http works correctly when reactions has never been accessed."""
        client = ApiClient("https://mock.service.url", mock_http_client)
        assert client._reactions is None

        new_http = Client(ClientOptions(base_url="https://new.service.url"))
        client.http = new_http

        assert client._http is new_http
        assert client._reactions is None

    def test_http_setter_also_updates_reactions_when_instantiated(self, mock_http_client):
        """Test that setting http propagates to the reactions client when it exists."""
        client = ApiClient("https://mock.service.url", mock_http_client)
        _ = client.reactions
        assert client._reactions is not None

        new_http = Client(ClientOptions(base_url="https://new.service.url"))
        client.http = new_http

        assert client._reactions.http is new_http
        assert client._http is new_http


@pytest.mark.unit
class TestApiClientDeprecatedAccessors:
    """The bots and reactions accessors are deprecated but still supported."""

    def test_reactions_accessor_warns(self, mock_http_client):
        client = ApiClient("https://mock.service.url", mock_http_client)
        with pytest.warns(DeprecationWarning):
            reactions = client.reactions
        assert isinstance(reactions, ReactionClient)

    def test_bots_accessor_warns(self, mock_http_client):
        client = ApiClient("https://mock.service.url", mock_http_client)
        with pytest.warns(DeprecationWarning):
            bots = client.bots
        assert bots.sign_in is not None

    @pytest.mark.asyncio
    async def test_deprecated_reactions_add_still_routes(self, mock_http_client):
        client = ApiClient("https://mock.service.url", mock_http_client)
        with pytest.warns(DeprecationWarning):
            reactions = client.reactions

        with patch.object(reactions.http, "put", new_callable=AsyncMock) as mock_put:
            await reactions.add("conv-1", "act-1", "like")

        mock_put.assert_called_once_with(
            "https://mock.service.url/v3/conversations/conv-1/activities/act-1/reactions/like"
        )
