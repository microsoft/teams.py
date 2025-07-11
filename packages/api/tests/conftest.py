"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import os
from pathlib import Path
from typing import Any, Optional

import httpx
import pytest
from dotenv import load_dotenv
from microsoft.teams.api import (
    Account,
    ClientCredentials,
    TokenCredentials,
)
from microsoft.teams.api.clients.conversation import ActivityParams
from microsoft.teams.api.models.conversation import ConversationResource
from microsoft.teams.common.http import Client, ClientOptions

try:
    # Load .env file if it exists
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        load_dotenv(env_file)
except ImportError:
    pass  # python-dotenv not available, use system environment


@pytest.fixture
def mock_transport():
    """Create a mock HTTP transport for testing."""

    def handler(request: httpx.Request) -> httpx.Response:
        # Default response
        response_data: Any = {
            "ok": True,
            "url": str(request.url),
            "method": request.method,
            "headers": dict(request.headers.items()),
        }

        # Handle specific endpoints with realistic responses
        if "GetAadTokens" in str(request.url):
            response_data = {
                "https://graph.microsoft.com": {
                    "connectionName": "test_connection",
                    "token": "mock_graph_token_123",
                    "expiration": "2024-12-01T12:00:00Z",
                },
                "https://api.botframework.com": {
                    "connectionName": "test_connection",
                    "token": "mock_botframework_token_123",
                    "expiration": "2024-12-01T12:00:00Z",
                },
            }
        elif "GetTokenStatus" in str(request.url):
            response_data = [
                {
                    "channelId": "test_channel_id",
                    "connectionName": "test_connection",
                    "hasToken": True,
                    "serviceProviderDisplayName": "Test Provider",
                }
            ]
        elif "exchange" in str(request.url):
            response_data = {
                "connectionName": "test_connection",
                "token": "mock_exchanged_token_123",
                "expiration": "2024-12-01T12:00:00Z",
            }
        elif "GetToken" in str(request.url):
            response_data = {
                "connectionName": "test_connection",
                "token": "mock_access_token_123",
                "expiration": "2024-12-01T12:00:00Z",
            }
        elif "GetSignInUrl" in str(request.url):
            response_data = "https://mock-signin.url/auth"
        elif "GetSignInResource" in str(request.url):
            response_data = {
                "signInLink": "https://mock-signin.url/auth",
                "tokenExchangeResource": {"id": "mock_resource_id"},
            }
        elif "/v3/teams/" in str(request.url) and "/conversations" in str(request.url):
            response_data = [
                {
                    "id": "mock_channel_id_1",
                    "name": "General",
                    "type": "standard",
                },
                {
                    "id": "mock_channel_id_2",
                    "name": "Random",
                    "type": "standard",
                },
            ]
        elif "/conversations/" in str(request.url) and str(request.url).endswith("/members"):
            response_data = [
                {
                    "id": "mock_member_id",
                    "name": "Mock Member",
                    "aadObjectId": "mock_aad_id",
                }
            ]
        elif "/conversations/" in str(request.url) and "/members/" in str(request.url) and request.method == "GET":
            response_data = {
                "id": "mock_member_id",
                "name": "Mock Member",
                "aadObjectId": "mock_aad_id",
            }
        elif "/conversations" in str(request.url) and request.method == "GET":
            response_data = {
                "conversations": [
                    {
                        "id": "mock_conversation_id",
                        "conversationType": "personal",
                        "isGroup": True,
                    }
                ],
                "continuationToken": "mock_continuation_token",
            }
        elif "/conversations" in str(request.url) and request.method == "POST":
            response_data = {
                "id": "mock_conversation_id",
                "type": "message",
                "activityId": "mock_activity_id",
                "serviceUrl": "https://mock.service.url",
            }
        elif "/activities" in str(request.url):
            if request.method == "POST":
                response_data = {
                    "id": "mock_activity_id",
                    "type": "message",
                    "text": "Mock activity response",
                }
            elif request.method == "PUT":
                response_data = {
                    "id": "mock_activity_id",
                    "type": "message",
                    "text": "Updated mock activity",
                }
        elif "oauth2/v2.0/token" in str(request.url):
            response_data = {
                "token_type": "Bearer",
                "expires_in": 3600,
                "access_token": "mock_oauth_token_123",
            }
        elif "/v1/meetings/" in str(request.url) and "/participants/" in str(request.url):
            response_data = {
                "user": {
                    "id": "mock_participant_id",
                    "name": "Mock Participant",
                    "aadObjectId": "mock_participant_aad_id",
                },
                "meeting": {
                    "id": "mock_meeting_id",
                    "title": "Mock Meeting",
                    "type": "meetingChat",
                },
                "conversation": {
                    "id": "mock_conversation_id",
                    "conversationType": "groupChat",
                    "tenantId": "mock_tenant_id",
                },
            }
        elif "/v1/meetings/" in str(request.url):
            response_data = {
                "id": "mock_meeting_id",
                "details": {
                    "id": "mock_meeting_id",
                    "title": "Mock Meeting",
                    "type": "meetingChat",
                    "joinUrl": "https://teams.microsoft.com/l/meetup-join/mock_meeting",
                    "msGraphResourceId": "mock_graph_resource_id",
                },
                "conversation": {
                    "id": "mock_conversation_id",
                    "conversationType": "groupChat",
                    "tenantId": "mock_tenant_id",
                },
                "organizer": {
                    "id": "mock_organizer_id",
                    "name": "Mock Organizer",
                    "aadObjectId": "mock_organizer_aad_id",
                },
            }
        elif "/v3/teams/" in str(request.url):
            response_data = {
                "id": "mock_team_id",
                "name": "Mock Team",
                "type": "standard",
                "aadGroupId": "mock_aad_group_id",
                "channelCount": 5,
                "memberCount": 15,
            }

        return httpx.Response(
            status_code=200,
            json=response_data,
            headers={"content-type": "application/json"},
        )

    return httpx.MockTransport(handler)


@pytest.fixture
def mock_http_client(mock_transport):
    """Create a mock HTTP client with transport."""
    client = Client(ClientOptions(base_url="https://mock.api.com"))
    client.http._transport = mock_transport
    return client


@pytest.fixture
def mock_client_credentials():
    """Create mock client credentials for testing."""
    return ClientCredentials(
        client_id="mock_client_id",
        client_secret="mock_client_secret",
        tenant_id="mock_tenant_id",
    )


@pytest.fixture
def mock_token_credentials():
    """Create mock token credentials for testing."""

    async def mock_token_factory(scope: str, tenant_id: Optional[str] = None) -> str:
        return f"mock_token_for_{scope.replace('/', '_')}"

    return TokenCredentials(client_id="mock_client_id", token=mock_token_factory, tenant_id="mock_tenant_id")


@pytest.fixture
def mock_account():
    """Create a mock account for testing."""
    return Account(
        id="mock_account_id",
        name="Mock Account",
        aad_object_id="mock_aad_object_id",
    )


@pytest.fixture
def mock_activity():
    """Create a mock activity for testing."""
    return ActivityParams(
        **{"type": "message", "text": "Mock activity text", "from_": Account(id="sender_id", name="Sender")}
    )


@pytest.fixture
def mock_conversation_resource():
    """Create a mock conversation resource for testing."""
    return ConversationResource(
        id="mock_conversation_id",
        activity_id="mock_activity_id",
        service_url="https://mock.service.url",
    )


@pytest.fixture
def integration_config():
    """Load configuration for integration tests from environment variables."""
    return {
        "client_id": os.getenv("TEAMS_CLIENT_ID"),
        "client_secret": os.getenv("TEAMS_CLIENT_SECRET"),
        "tenant_id": os.getenv("TEAMS_TENANT_ID", None),
        "service_url": os.getenv("TEAMS_SERVICE_URL", "https://smba.trafficmanager.net/teams"),
        "bot_id": os.getenv("TEAMS_BOT_ID"),
        "conversation_id": os.getenv("TEAMS_CONVERSATION_ID"),
        "user_id": os.getenv("TEAMS_USER_ID"),
        "channel_id": os.getenv("TEAMS_CHANNEL_ID"),
        "connection_name": os.getenv("TEAMS_CONNECTION_NAME"),
    }


@pytest.fixture
def skip_if_no_credentials(integration_config):
    """Skip integration tests if credentials are not provided."""
    required_fields = ["client_id", "client_secret"]
    missing_fields = [field for field in required_fields if not integration_config.get(field)]

    if missing_fields:
        pytest.skip(f"Integration test credentials missing: {', '.join(missing_fields)}")

    return integration_config


# Marks for test organization
def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line("markers", "unit: Unit tests that run with mocked dependencies")
    config.addinivalue_line("markers", "integration: Integration tests that require real API credentials")
    config.addinivalue_line("markers", "slow: Tests that may take longer to run")


def pytest_collection_modifyitems(config, items):
    """Automatically mark tests based on their location."""
    for item in items:
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
