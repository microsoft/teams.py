"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

from unittest.mock import AsyncMock, patch

import pytest
from microsoft_teams.api.clients.reaction import ReactionClient


@pytest.mark.unit
class TestReactionClient:
    """Unit tests for ReactionClient."""

    def test_reaction_client_initialization(self, mock_http_client):
        """Test ReactionClient initialization."""
        service_url = "https://test.service.url"
        client = ReactionClient(service_url, mock_http_client)

        assert client.http == mock_http_client
        assert client.service_url == service_url

    def test_reaction_client_initialization_with_options(self):
        """Test ReactionClient initialization with ClientOptions."""
        service_url = "https://test.service.url"
        client = ReactionClient(service_url)

        assert client.http is not None
        assert client.service_url == service_url

    @pytest.mark.asyncio
    async def test_add_reaction(self, mock_http_client):
        """Test adding a reaction to an activity."""
        service_url = "https://test.service.url"
        client = ReactionClient(service_url, mock_http_client)

        conversation_id = "test_conversation_id"
        activity_id = "test_activity_id"
        reaction_type = "like"

        with patch.object(mock_http_client, "put", new_callable=AsyncMock) as mock_put:
            await client.add(conversation_id, activity_id, reaction_type)

        expected_url = (
            f"{service_url}/v3/conversations/{conversation_id}/activities/{activity_id}/reactions/{reaction_type}"
        )
        mock_put.assert_called_once_with(expected_url)

    @pytest.mark.asyncio
    async def test_add_heart_reaction(self, mock_http_client):
        """Test adding a heart reaction to an activity."""
        service_url = "https://test.service.url"
        client = ReactionClient(service_url, mock_http_client)

        conversation_id = "test_conversation_id"
        activity_id = "test_activity_id"
        reaction_type = "heart"

        with patch.object(mock_http_client, "put", new_callable=AsyncMock) as mock_put:
            await client.add(conversation_id, activity_id, reaction_type)

        expected_url = (
            f"{service_url}/v3/conversations/{conversation_id}/activities/{activity_id}/reactions/{reaction_type}"
        )
        mock_put.assert_called_once_with(expected_url)

    @pytest.mark.asyncio
    async def test_delete_reaction(self, mock_http_client):
        """Test removing a reaction from an activity."""
        service_url = "https://test.service.url"
        client = ReactionClient(service_url, mock_http_client)

        conversation_id = "test_conversation_id"
        activity_id = "test_activity_id"
        reaction_type = "like"

        with patch.object(mock_http_client, "delete", new_callable=AsyncMock) as mock_delete:
            await client.delete(conversation_id, activity_id, reaction_type)

        expected_url = (
            f"{service_url}/v3/conversations/{conversation_id}/activities/{activity_id}/reactions/{reaction_type}"
        )
        mock_delete.assert_called_once_with(expected_url)

    @pytest.mark.asyncio
    async def test_delete_laugh_reaction(self, mock_http_client):
        """Test removing a laugh reaction from an activity."""
        service_url = "https://test.service.url"
        client = ReactionClient(service_url, mock_http_client)

        conversation_id = "test_conversation_id"
        activity_id = "test_activity_id"
        reaction_type = "laugh"

        with patch.object(mock_http_client, "delete", new_callable=AsyncMock) as mock_delete:
            await client.delete(conversation_id, activity_id, reaction_type)

        expected_url = (
            f"{service_url}/v3/conversations/{conversation_id}/activities/{activity_id}/reactions/{reaction_type}"
        )
        mock_delete.assert_called_once_with(expected_url)
