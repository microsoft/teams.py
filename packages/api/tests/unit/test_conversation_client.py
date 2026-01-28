"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

import json

import pytest
from microsoft_teams.api.clients.conversation import ConversationClient
from microsoft_teams.api.clients.conversation.params import (
    CreateConversationParams,
    GetConversationsParams,
)
from microsoft_teams.api.models import TeamsChannelAccount
from microsoft_teams.common.http import Client, ClientOptions


@pytest.mark.unit
class TestConversationClient:
    """Unit tests for ConversationClient."""

    def test_conversation_client_initialization(self, mock_http_client):
        """Test ConversationClient initialization."""
        service_url = "https://test.service.url"
        client = ConversationClient(service_url, mock_http_client)

        assert client.http == mock_http_client
        assert client.service_url == service_url
        assert client.activities_client is not None
        assert client.members_client is not None

    def test_conversation_client_initialization_with_options(self):
        """Test ConversationClient initialization with ClientOptions."""

        service_url = "https://test.service.url"
        options = ClientOptions(base_url="https://test.api.com")
        client = ConversationClient(service_url, options)

        assert client.http is not None
        assert client.service_url == service_url

    @pytest.mark.asyncio
    async def test_get_conversations(self, request_capture):
        """Test getting conversations with continuation token."""
        service_url = "https://test.service.url"
        client = ConversationClient(service_url, request_capture)

        params = GetConversationsParams(continuation_token="test_token")
        response = await client.get(params)

        # Validate response
        assert response.conversations is not None
        assert isinstance(response.conversations, list)
        assert response.continuation_token is not None

        # Validate request details
        last_request = request_capture._capture.last_request
        assert last_request.method == "GET"
        assert str(last_request.url) == "https://test.service.url/v3/conversations?continuationToken=test_token"

    @pytest.mark.asyncio
    async def test_get_conversations_without_params(self, request_capture):
        """Test getting conversations without parameters."""
        service_url = "https://test.service.url"
        client = ConversationClient(service_url, request_capture)

        response = await client.get()

        # Validate response
        assert response.conversations is not None
        assert isinstance(response.conversations, list)

        # Validate request details
        last_request = request_capture._capture.last_request
        assert last_request.method == "GET"
        assert str(last_request.url) == "https://test.service.url/v3/conversations"

    @pytest.mark.asyncio
    async def test_create_conversation(self, request_capture, mock_account, mock_activity):
        """Test creating a conversation."""
        service_url = "https://test.service.url"
        client = ConversationClient(service_url, request_capture)

        params = CreateConversationParams(
            is_group=True,
            bot=mock_account,
            members=[mock_account],
            topic_name="Test Conversation",
            tenant_id="test_tenant_id",
            activity=mock_activity,
            channel_data={"custom": "data"},
        )

        response = await client.create(params)

        # Validate response
        assert response.id is not None
        assert response.activity_id is not None
        assert response.service_url is not None

        # Validate request details
        last_request = request_capture._capture.last_request
        assert last_request.method == "POST"
        assert str(last_request.url) == "https://test.service.url/v3/conversations"

        # Validate request payload

        payload = json.loads(last_request.content.decode("utf-8"))
        assert payload["isGroup"] is True
        assert payload["bot"]["id"] == mock_account.id
        assert payload["bot"]["name"] == mock_account.name
        assert len(payload["members"]) == 1
        assert payload["members"][0]["id"] == mock_account.id
        assert payload["topicName"] == "Test Conversation"
        assert payload["tenantId"] == "test_tenant_id"
        assert payload["activity"]["type"] == "message"
        assert payload["activity"]["text"] == "Mock activity text"
        assert payload["channelData"]["custom"] == "data"

    def test_activities_operations(self, mock_http_client):
        """Test activities operations object creation."""
        service_url = "https://test.service.url"
        client = ConversationClient(service_url, mock_http_client)

        conversation_id = "test_conversation_id"
        activities = client.activities(conversation_id)

        assert activities._conversation_id == conversation_id
        assert activities._client == client

    def test_members_operations(self, mock_http_client):
        """Test members operations object creation."""
        service_url = "https://test.service.url"
        client = ConversationClient(service_url, mock_http_client)

        conversation_id = "test_conversation_id"
        members = client.members(conversation_id)

        assert members._conversation_id == conversation_id
        assert members._client == client


@pytest.mark.unit
@pytest.mark.asyncio
class TestConversationActivityOperations:
    """Unit tests for ConversationClient activity operations."""

    async def test_activity_create(self, request_capture, mock_activity):
        """Test creating an activity."""
        service_url = "https://test.service.url"
        client = ConversationClient(service_url, request_capture)

        conversation_id = "test_conversation_id"
        activities = client.activities(conversation_id)

        result = await activities.create(mock_activity)

        # Validate response
        assert result is not None
        assert result.id is not None

        # Validate request details
        last_request = request_capture._capture.last_request
        assert last_request.method == "POST"
        assert str(last_request.url) == f"https://test.service.url/v3/conversations/{conversation_id}/activities"

        # Validate request payload

        payload = json.loads(last_request.content.decode("utf-8"))
        assert payload["type"] == "message"
        assert payload["text"] == "Mock activity text"
        assert payload["from"]["id"] == "sender_id"

    async def test_activity_update(self, request_capture, mock_activity):
        """Test updating an activity."""
        service_url = "https://test.service.url"
        client = ConversationClient(service_url, request_capture)

        conversation_id = "test_conversation_id"
        activity_id = "test_activity_id"
        activities = client.activities(conversation_id)

        result = await activities.update(activity_id, mock_activity)

        # Validate response
        assert result is not None
        assert result.id is not None

        # Validate request details
        last_request = request_capture._capture.last_request
        assert last_request.method == "PUT"
        assert (
            str(last_request.url)
            == f"https://test.service.url/v3/conversations/{conversation_id}/activities/{activity_id}"
        )

        # Validate request payload

        payload = json.loads(last_request.content.decode("utf-8"))
        assert payload["type"] == "message"
        assert payload["text"] == "Mock activity text"

    async def test_activity_reply(self, request_capture, mock_activity):
        """Test replying to an activity."""
        service_url = "https://test.service.url"
        client = ConversationClient(service_url, request_capture)

        conversation_id = "test_conversation_id"
        activity_id = "test_activity_id"
        activities = client.activities(conversation_id)

        result = await activities.reply(activity_id, mock_activity)

        # Validate response
        assert result is not None
        assert result.id is not None

        # Validate request details
        last_request = request_capture._capture.last_request
        assert last_request.method == "POST"
        assert (
            str(last_request.url)
            == f"https://test.service.url/v3/conversations/{conversation_id}/activities/{activity_id}"
        )

        # Validate request payload

        payload = json.loads(last_request.content.decode("utf-8"))
        assert payload["type"] == "message"
        assert payload["text"] == "Mock activity text"
        assert payload["replyToId"] == activity_id

    async def test_activity_delete(self, request_capture):
        """Test deleting an activity."""
        service_url = "https://test.service.url"
        client = ConversationClient(service_url, request_capture)

        conversation_id = "test_conversation_id"
        activity_id = "test_activity_id"
        activities = client.activities(conversation_id)

        # Should not raise an exception
        await activities.delete(activity_id)

        # Validate request details
        last_request = request_capture._capture.last_request
        assert last_request.method == "DELETE"
        assert (
            str(last_request.url)
            == f"https://test.service.url/v3/conversations/{conversation_id}/activities/{activity_id}"
        )

    async def test_activity_get_members(self, request_capture):
        """Test getting activity members."""
        service_url = "https://test.service.url"
        client = ConversationClient(service_url, request_capture)

        conversation_id = "test_conversation_id"
        activity_id = "test_activity_id"
        activities = client.activities(conversation_id)

        result = await activities.get_members(activity_id)

        # Validate response
        assert result is not None
        assert len(result) > 0

        # Validate request details
        last_request = request_capture._capture.last_request
        assert last_request.method == "GET"
        assert (
            str(last_request.url)
            == f"https://test.service.url/v3/conversations/{conversation_id}/activities/{activity_id}/members"
        )


@pytest.mark.unit
@pytest.mark.asyncio
class TestConversationMemberOperations:
    """Unit tests for ConversationClient member operations."""

    async def test_member_get_all(self, request_capture):
        """Test getting all members returns TeamsChannelAccount instances."""
        service_url = "https://test.service.url"
        client = ConversationClient(service_url, request_capture)

        conversation_id = "test_conversation_id"
        members = client.members(conversation_id)

        result = await members.get_all()

        # Validate response
        assert result is not None
        assert len(result) > 0
        assert isinstance(result[0], TeamsChannelAccount)
        assert result[0].id == "mock_member_id"
        assert result[0].name == "Mock Member"
        assert result[0].object_id == "mock_object_id"

        # Validate request details
        last_request = request_capture._capture.last_request
        assert last_request.method == "GET"
        assert str(last_request.url) == f"https://test.service.url/v3/conversations/{conversation_id}/members"

    async def test_member_get(self, request_capture):
        """Test getting a specific member returns TeamsChannelAccount instance."""
        service_url = "https://test.service.url"
        client = ConversationClient(service_url, request_capture)

        conversation_id = "test_conversation_id"
        member_id = "test_member_id"
        members = client.members(conversation_id)

        result = await members.get(member_id)

        # Validate response
        assert result is not None
        assert isinstance(result, TeamsChannelAccount)
        assert result.id == "mock_member_id"
        assert result.name == "Mock Member"
        assert result.object_id == "mock_object_id"

        # Validate request details
        last_request = request_capture._capture.last_request
        assert last_request.method == "GET"
        assert (
            str(last_request.url) == f"https://test.service.url/v3/conversations/{conversation_id}/members/{member_id}"
        )

    async def test_member_delete(self, request_capture):
        """Test deleting a member."""
        service_url = "https://test.service.url"
        client = ConversationClient(service_url, request_capture)

        conversation_id = "test_conversation_id"
        member_id = "test_member_id"
        members = client.members(conversation_id)

        # Should not raise an exception
        await members.delete(member_id)

        # Validate request details
        last_request = request_capture._capture.last_request
        assert last_request.method == "DELETE"
        assert (
            str(last_request.url) == f"https://test.service.url/v3/conversations/{conversation_id}/members/{member_id}"
        )


@pytest.mark.unit
class TestConversationClientHttpClientSharing:
    """Test that HTTP client is properly shared between sub-clients."""

    def test_http_client_sharing(self, mock_http_client):
        """Test that all sub-clients share the same HTTP client."""
        service_url = "https://test.service.url"
        client = ConversationClient(service_url, mock_http_client)

        assert client.activities_client.http == mock_http_client
        assert client.members_client.http == mock_http_client

    def test_http_client_update_propagates(self, mock_http_client):
        """Test that updating HTTP client propagates to sub-clients."""

        service_url = "https://test.service.url"
        client = ConversationClient(service_url, mock_http_client)
        new_http_client = Client(ClientOptions(base_url="https://new.api.com"))

        # Update the HTTP client
        client.http = new_http_client

        assert client.http == new_http_client

        assert client.activities_client.http == new_http_client
        assert client.members_client.http == new_http_client
