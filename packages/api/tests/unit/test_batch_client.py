"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

import pytest
from microsoft_teams.api.activities.message.message import MessageActivityInput
from microsoft_teams.api.clients.batch import (
    BatchChannelsParams,
    BatchClient,
    BatchTeamParams,
    BatchTenantParams,
    BatchUsersParams,
)
from microsoft_teams.api.models import Account
from microsoft_teams.api.models.batch import BatchOperationResult
from microsoft_teams.common.http import Client, ClientOptions


@pytest.mark.unit
class TestBatchClient:
    """Unit tests for BatchClient."""

    def test_batch_client_strips_trailing_slash(self, mock_http_client):
        """Test BatchClient strips trailing slash from service_url."""
        service_url = "https://test.service.url/"
        client = BatchClient(service_url, mock_http_client)

        assert client.service_url == "https://test.service.url"

    def test_http_client_property(self, mock_http_client):
        """Test HTTP client property getter and setter."""
        service_url = "https://test.service.url"
        client = BatchClient(service_url, mock_http_client)

        assert client.http == mock_http_client

        new_http_client = Client(ClientOptions(base_url="https://new.api.com"))
        client.http = new_http_client

        assert client.http == new_http_client

    @pytest.mark.asyncio
    async def test_send_to_tenant(self, mock_http_client):
        """Test sending a message to all users in a tenant."""
        service_url = "https://test.service.url"
        client = BatchClient(service_url, mock_http_client)

        result = await client.send_to_tenant(
            BatchTenantParams(
                tenant_id="mock_tenant_id",
                activity=MessageActivityInput(text="hello"),
            )
        )

        assert isinstance(result, BatchOperationResult)
        assert result.operation_id == "mock_operation_id"

    @pytest.mark.asyncio
    async def test_send_to_users(self, mock_http_client):
        """Test sending a message to a list of users."""
        service_url = "https://test.service.url"
        client = BatchClient(service_url, mock_http_client)

        result = await client.send_to_users(
            BatchUsersParams(
                tenant_id="mock_tenant_id",
                members=[Account(id=f"29:user-{i}") for i in range(5)],
                activity=MessageActivityInput(text="hello"),
            )
        )

        assert isinstance(result, BatchOperationResult)
        assert result.operation_id == "mock_operation_id"

    @pytest.mark.asyncio
    async def test_send_to_team(self, mock_http_client):
        """Test sending a message to all members of a team."""
        service_url = "https://test.service.url"
        client = BatchClient(service_url, mock_http_client)

        result = await client.send_to_team(
            BatchTeamParams(
                tenant_id="mock_tenant_id",
                team_id="19:mock@thread.tacv2",
                activity=MessageActivityInput(text="hello"),
            )
        )

        assert isinstance(result, BatchOperationResult)
        assert result.operation_id == "mock_operation_id"

    @pytest.mark.asyncio
    async def test_send_to_channels(self, mock_http_client):
        """Test sending a message to a list of channels."""
        service_url = "https://test.service.url"
        client = BatchClient(service_url, mock_http_client)

        result = await client.send_to_channels(
            BatchChannelsParams(
                tenant_id="mock_tenant_id",
                members=[Account(id="19:mock-channel@thread.tacv2")],
                activity=MessageActivityInput(text="hello"),
            )
        )

        assert isinstance(result, BatchOperationResult)
        assert result.operation_id == "mock_operation_id"
