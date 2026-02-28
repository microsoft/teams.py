"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

import pytest
from microsoft_teams.api.clients.conversation import ConversationClient
from microsoft_teams.api.clients.conversation.params import (
    CreateConversationParams,
    GetConversationsParams,
)
from microsoft_teams.api.models import ConversationResource, TeamsChannelAccount
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
    async def test_get_conversations(self, mock_http_client):
        """Test getting conversations."""
        service_url = "https://test.service.url"
        client = ConversationClient(service_url, mock_http_client)

        params = GetConversationsParams(continuation_token="test_token")
        response = await client.get(params)

        assert response.conversations is not None
        assert isinstance(response.conversations, list)
        assert response.continuation_token is not None

    @pytest.mark.asyncio
    async def test_get_conversations_without_params(self, mock_http_client):
        """Test getting conversations without parameters."""
        service_url = "https://test.service.url"
        client = ConversationClient(service_url, mock_http_client)

        response = await client.get()

        assert response.conversations is not None
        assert isinstance(response.conversations, list)

    @pytest.mark.asyncio
    async def test_create_conversation(self, mock_http_client, mock_account, mock_activity):
        """Test creating a conversation with an activity."""
        service_url = "https://test.service.url"
        client = ConversationClient(service_url, mock_http_client)

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

        assert response.id is not None
        assert response.activity_id is not None
        assert response.service_url is not None

    @pytest.mark.asyncio
    async def test_create_conversation_without_activity(self, mock_http_client, mock_account):
        """Test creating a conversation without an activity."""
        service_url = "https://test.service.url"
        client = ConversationClient(service_url, mock_http_client)

        params = CreateConversationParams(
            is_group=True,
            bot=mock_account,
            members=[mock_account],
            topic_name="Test Conversation",
            tenant_id="test_tenant_id",
        )

        response = await client.create(params)

        assert response.id is not None
        assert response.activity_id is None
        assert response.service_url is not None

    def test_conversation_resource_with_all_fields(self):
        """Test that ConversationResource correctly handles all fields present."""
        resource = ConversationResource.model_validate(
            {
                "id": "test_id",
                "activityId": "test_activity",
                "serviceUrl": "https://test.url",
            }
        )
        assert resource.id == "test_id"
        assert resource.activity_id == "test_activity"
        assert resource.service_url == "https://test.url"

    def test_conversation_resource_without_activity_id(self):
        """Test that ConversationResource handles missing activityId."""
        resource = ConversationResource.model_validate(
            {
                "id": "test_id",
                "serviceUrl": "https://test.url",
            }
        )
        assert resource.id == "test_id"
        assert resource.activity_id is None
        assert resource.service_url == "https://test.url"

    def test_conversation_resource_without_service_url(self):
        """Test that ConversationResource handles missing serviceUrl."""
        resource = ConversationResource.model_validate(
            {
                "id": "test_id",
                "activityId": "test_activity",
            }
        )
        assert resource.id == "test_id"
        assert resource.activity_id == "test_activity"
        assert resource.service_url is None

    def test_conversation_resource_with_only_required_fields(self):
        """Test that ConversationResource handles only the required id field."""
        resource = ConversationResource.model_validate(
            {
                "id": "test_id",
            }
        )
        assert resource.id == "test_id"
        assert resource.activity_id is None
        assert resource.service_url is None

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

    async def test_activity_create(self, mock_http_client, mock_activity):
        """Test creating an activity."""
        service_url = "https://test.service.url"
        client = ConversationClient(service_url, mock_http_client)

        conversation_id = "test_conversation_id"
        activities = client.activities(conversation_id)

        result = await activities.create(mock_activity)

        assert result is not None

    async def test_activity_update(self, mock_http_client, mock_activity):
        """Test updating an activity."""
        service_url = "https://test.service.url"
        client = ConversationClient(service_url, mock_http_client)

        conversation_id = "test_conversation_id"
        activity_id = "test_activity_id"
        activities = client.activities(conversation_id)

        result = await activities.update(activity_id, mock_activity)

        assert result is not None

    async def test_activity_reply(self, mock_http_client, mock_activity):
        """Test replying to an activity."""
        service_url = "https://test.service.url"
        client = ConversationClient(service_url, mock_http_client)

        conversation_id = "test_conversation_id"
        activity_id = "test_activity_id"
        activities = client.activities(conversation_id)

        result = await activities.reply(activity_id, mock_activity)

        assert result is not None

    async def test_activity_delete(self, mock_http_client):
        """Test deleting an activity."""
        service_url = "https://test.service.url"
        client = ConversationClient(service_url, mock_http_client)

        conversation_id = "test_conversation_id"
        activity_id = "test_activity_id"
        activities = client.activities(conversation_id)

        # Should not raise an exception
        await activities.delete(activity_id)

    async def test_activity_get_members(self, mock_http_client):
        """Test getting activity members."""
        service_url = "https://test.service.url"
        client = ConversationClient(service_url, mock_http_client)

        conversation_id = "test_conversation_id"
        activity_id = "test_activity_id"
        activities = client.activities(conversation_id)

        result = await activities.get_members(activity_id)

        assert result is not None


@pytest.mark.unit
@pytest.mark.asyncio
class TestConversationMemberOperations:
    """Unit tests for ConversationClient member operations."""

    async def test_member_get_all(self, mock_http_client):
        """Test getting all members returns TeamsChannelAccount instances."""
        service_url = "https://test.service.url"
        client = ConversationClient(service_url, mock_http_client)

        conversation_id = "test_conversation_id"
        members = client.members(conversation_id)

        result = await members.get_all()

        assert result is not None
        assert len(result) > 0
        assert isinstance(result[0], TeamsChannelAccount)
        assert result[0].id == "mock_member_id"
        assert result[0].name == "Mock Member"
        assert result[0].aad_object_id == "mock_aad_object_id"

    async def test_member_get(self, mock_http_client):
        """Test getting a specific member returns TeamsChannelAccount instance."""
        service_url = "https://test.service.url"
        client = ConversationClient(service_url, mock_http_client)

        conversation_id = "test_conversation_id"
        member_id = "test_member_id"
        members = client.members(conversation_id)

        result = await members.get(member_id)

        assert result is not None
        assert isinstance(result, TeamsChannelAccount)
        assert result.id == "mock_member_id"
        assert result.name == "Mock Member"
        assert result.aad_object_id == "mock_aad_object_id"

    async def test_member_delete(self, mock_http_client):
        """Test deleting a member."""
        service_url = "https://test.service.url"
        client = ConversationClient(service_url, mock_http_client)

        conversation_id = "test_conversation_id"
        member_id = "test_member_id"
        members = client.members(conversation_id)

        # Should not raise an exception
        await members.delete(member_id)


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


@pytest.mark.unit
@pytest.mark.asyncio
class TestTargetedActivityOperations:
    """Unit tests for targeted activity operations."""

    async def test_activity_create_targeted(self, mock_http_client, mock_activity):
        """Test creating a targeted activity."""
        service_url = "https://test.service.url"
        client = ConversationClient(service_url, mock_http_client)

        conversation_id = "test_conversation_id"
        activities = client.activities(conversation_id)

        result = await activities.create_targeted(mock_activity)

        assert result is not None

    async def test_activity_update_targeted(self, mock_http_client, mock_activity):
        """Test updating a targeted activity."""
        service_url = "https://test.service.url"
        client = ConversationClient(service_url, mock_http_client)

        conversation_id = "test_conversation_id"
        activity_id = "test_activity_id"
        activities = client.activities(conversation_id)

        result = await activities.update_targeted(activity_id, mock_activity)

        assert result is not None

    async def test_activity_delete_targeted(self, mock_http_client):
        """Test deleting a targeted activity."""
        service_url = "https://test.service.url"
        client = ConversationClient(service_url, mock_http_client)

        conversation_id = "test_conversation_id"
        activity_id = "test_activity_id"
        activities = client.activities(conversation_id)

        # Should not raise an exception
        await activities.delete_targeted(activity_id)
