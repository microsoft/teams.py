"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

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

        await client.add(conversation_id, activity_id, reaction_type)

        # Verify the request was made to the correct URL
        # The mock transport will handle the request

    @pytest.mark.asyncio
    async def test_add_heart_reaction(self, mock_http_client):
        """Test adding a heart reaction to an activity."""
        service_url = "https://test.service.url"
        client = ReactionClient(service_url, mock_http_client)

        conversation_id = "test_conversation_id"
        activity_id = "test_activity_id"
        reaction_type = "heart"

        await client.add(conversation_id, activity_id, reaction_type)

    @pytest.mark.asyncio
    async def test_delete_reaction(self, mock_http_client):
        """Test removing a reaction from an activity."""
        service_url = "https://test.service.url"
        client = ReactionClient(service_url, mock_http_client)

        conversation_id = "test_conversation_id"
        activity_id = "test_activity_id"
        reaction_type = "like"

        await client.delete(conversation_id, activity_id, reaction_type)

        # Verify the request was made to the correct URL

    @pytest.mark.asyncio
    async def test_delete_laugh_reaction(self, mock_http_client):
        """Test removing a laugh reaction from an activity."""
        service_url = "https://test.service.url"
        client = ReactionClient(service_url, mock_http_client)

        conversation_id = "test_conversation_id"
        activity_id = "test_activity_id"
        reaction_type = "laugh"

        await client.delete(conversation_id, activity_id, reaction_type)
