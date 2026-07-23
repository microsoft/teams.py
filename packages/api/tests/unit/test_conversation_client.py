"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

import json
from contextlib import contextmanager
from typing import Any, Iterator
from unittest.mock import AsyncMock, call, patch

import httpx
import pytest
from microsoft_teams.api.auth.cloud_environment import PUBLIC, with_overrides
from microsoft_teams.api.clients import ApiClient
from microsoft_teams.api.clients.conversation import ConversationClient
from microsoft_teams.api.clients.conversation.params import CreateConversationParams
from microsoft_teams.api.diagnostics._outbound import ApiOutboundTelemetryMetadata
from microsoft_teams.api.models import AgentUser, ConversationResource, PagedMembersResult, TeamsChannelAccount
from microsoft_teams.common.http import Client, ClientOptions
from opentelemetry.trace import Span, SpanKind


class RecordingSpan:
    def __init__(self, name: str, options: dict[str, Any], attributes: dict[str, str]):
        self.name = name
        self.options = options
        self.attributes = attributes
        self.ended_count = 0

    def set_attribute(self, key: str, value: str) -> None:
        self.attributes[key] = value


class RecordingTracer:
    def __init__(self):
        self.spans: list[RecordingSpan] = []

    @contextmanager
    def start_as_current_span(self, name: str, **kwargs: Any) -> Iterator[RecordingSpan]:
        attributes = kwargs.pop("attributes", {})
        span = RecordingSpan(name, kwargs, attributes)
        self.spans.append(span)
        try:
            yield span
        finally:
            span.ended_count += 1


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

    def test_conversation_client_strips_trailing_slash(self, mock_http_client):
        """Test ConversationClient strips trailing slash from service_url."""
        service_url = "https://test.service.url/"
        client = ConversationClient(service_url, mock_http_client)

        assert client.service_url == "https://test.service.url"
        assert client.activities_client.service_url == "https://test.service.url"
        assert client.members_client.service_url == "https://test.service.url"

    def test_conversation_client_initialization_with_options(self):
        """Test ConversationClient initialization with ClientOptions."""

        service_url = "https://test.service.url"
        options = ClientOptions(base_url="https://test.api.com")
        client = ConversationClient(service_url, options)

        assert client.http is not None
        assert client.service_url == service_url

    @pytest.mark.asyncio
    async def test_create_conversation(self, request_capture, mock_account, mock_activity):
        """Test creating a conversation with an activity."""
        service_url = "https://test.service.url"
        client = ConversationClient(service_url, request_capture)

        params = CreateConversationParams(
            members=[mock_account],
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
        payload = json.loads(last_request.content)
        assert payload["tenantId"] == "test_tenant_id"

    @pytest.mark.asyncio
    async def test_create_conversation_without_activity(self, request_capture, mock_account):
        """Test creating a conversation without an activity."""
        service_url = "https://test.service.url"
        client = ConversationClient(service_url, request_capture)

        params = CreateConversationParams(
            members=[mock_account],
            tenant_id="test_tenant_id",
        )

        response = await client.create(params)

        # Validate response
        assert response.id is not None
        assert response.activity_id is None
        assert response.service_url is not None

        # Validate request details
        last_request = request_capture._capture.last_request
        assert last_request.method == "POST"
        assert str(last_request.url) == "https://test.service.url/v3/conversations"

    @pytest.mark.asyncio
    async def test_create_conversation_uses_scoped_service_url(self, request_capture, mock_account):
        client = (
            ApiClient("https://test.service.url", request_capture)
            .from_service_url("https://override.service.url/")
            .conversations
        )
        params = CreateConversationParams(members=[mock_account], tenant_id="test_tenant_id")

        await client.create(params)

        request = request_capture._capture.last_request
        assert request.method == "POST"
        assert str(request.url) == "https://override.service.url/v3/conversations"

    @pytest.mark.asyncio
    async def test_create_conversation_uses_auth_provider_for_bot_token(self, request_capture, mock_account):
        calls = []

        class TestAuthProvider:
            def token(self, *, scope=None, agent_user=None):
                calls.append((scope, agent_user))
                return "bot-token"

        client = ApiClient("https://test.service.url", request_capture, auth_provider=TestAuthProvider()).conversations
        params = CreateConversationParams(members=[mock_account], tenant_id="test_tenant_id")

        await client.create(params)

        assert calls == [(None, None)]
        request = request_capture._capture.last_request
        assert request.headers["authorization"] == "Bearer bot-token"

    @pytest.mark.asyncio
    async def test_create_conversation_uses_agent_user(self, request_capture, mock_account):
        calls = []

        class TestAuthProvider:
            def token(self, *, scope=None, agent_user=None):
                calls.append((scope, agent_user))
                return "agent-user-token"

        identity = AgentUser("agent-app-instance-id", "agent-user-id", tenant_id="tenant-id")
        client = ApiClient(
            "https://test.service.url", request_capture, auth_provider=TestAuthProvider(), agent_user=identity
        ).conversations
        params = CreateConversationParams(members=[mock_account], tenant_id="test_tenant_id")

        await client.create(params)

        assert calls == [(None, identity)]
        request = request_capture._capture.last_request
        assert request.headers["authorization"] == "Bearer agent-user-token"

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
        payload = json.loads(last_request.content)
        assert payload["type"] == "message"

    async def test_activity_create_with_scoped_service_url(self, request_capture, mock_activity):
        """Test creating an activity with a scoped service URL."""
        client = ApiClient("https://default.service.url", request_capture).from_service_url(
            "https://override.service.url/"
        )

        await client.conversations.activities("test_conversation_id").create(mock_activity)

        last_request = request_capture._capture.last_request
        assert str(last_request.url) == "https://override.service.url/v3/conversations/test_conversation_id/activities"

    async def test_activity_create_uses_auth_provider_for_bot_token(self, request_capture, mock_activity):
        """Test creating an activity with an auth provider but no agent user."""
        calls = []

        class TestAuthProvider:
            def token(self, *, scope=None, agent_user=None):
                calls.append((scope, agent_user))
                return "bot-token"

        client = ApiClient("https://test.service.url", request_capture, auth_provider=TestAuthProvider()).conversations

        await client.activities("test_conversation_id").create(mock_activity)

        assert calls == [(None, None)]
        last_request = request_capture._capture.last_request
        assert last_request.headers["authorization"] == "Bearer bot-token"

    async def test_activity_create_uses_client_agent_user(self, request_capture, mock_activity):
        """Test creating an activity with the client's default agent user."""
        calls = []

        class TestAuthProvider:
            def token(self, *, scope=None, agent_user=None):
                calls.append((scope, agent_user))
                return "agent-user-token"

        cloud = with_overrides(PUBLIC, agent_bot_scope="agent-user-scope")
        identity = AgentUser("agent-app-instance-id", "agent-user-id", tenant_id="tenant-id")
        client = ApiClient(
            "https://test.service.url",
            request_capture,
            auth_provider=TestAuthProvider(),
            agent_user=identity,
            cloud=cloud,
        ).conversations

        await client.activities("test_conversation_id").create(mock_activity)

        assert calls == [(None, identity)]
        last_request = request_capture._capture.last_request
        assert last_request.headers["authorization"] == "Bearer agent-user-token"

    async def test_activity_create_scoped_agent_user_overrides_client_default(self, request_capture, mock_activity):
        """Test scoped agent user overrides the client's default identity."""
        calls = []

        class TestAuthProvider:
            def token(self, *, scope=None, agent_user=None):
                calls.append((scope, agent_user))
                return "override-token"

        default_identity = AgentUser("default-app-id", "default-user-id", tenant_id="default-tenant-id")
        override_identity = AgentUser("override-app-id", "override-user-id", tenant_id="override-tenant-id")
        client = (
            ApiClient(
                "https://test.service.url",
                request_capture,
                auth_provider=TestAuthProvider(),
                agent_user=default_identity,
            )
            .from_agent_user(override_identity)
            .conversations
        )

        await client.activities("test_conversation_id").create(mock_activity)

        assert calls == [(None, override_identity)]
        last_request = request_capture._capture.last_request
        assert last_request.headers["authorization"] == "Bearer override-token"

    async def test_flattened_activity_create_accepts_service_url_and_agent_user_kwargs(
        self, request_capture, mock_activity
    ):
        calls = []

        class TestAuthProvider:
            def token(self, *, scope=None, agent_user=None):
                calls.append((scope, agent_user))
                return "override-token"

        identity = AgentUser("override-app-id", "override-user-id", tenant_id="override-tenant-id")
        client = ApiClient(
            "https://default.service.url",
            request_capture,
            auth_provider=TestAuthProvider(),
        ).conversations

        await client.create_activity(
            "test_conversation_id",
            mock_activity,
            service_url="https://override.service.url/",
            agent_user=identity,
        )

        assert calls == [(None, identity)]
        last_request = request_capture._capture.last_request
        assert str(last_request.url) == "https://override.service.url/v3/conversations/test_conversation_id/activities"
        assert "authorization" in last_request.headers

    async def test_direct_activities_client_methods_accept_service_url_and_agent_user_kwargs(
        self, request_capture, mock_activity
    ):
        calls = []

        class TestAuthProvider:
            def token(self, *, scope=None, agent_user=None):
                calls.append((scope, agent_user))
                return "override-token"

        identity = AgentUser("override-app-id", "override-user-id", tenant_id="override-tenant-id")
        activities_client = ApiClient(
            "https://default.service.url",
            request_capture,
            auth_provider=TestAuthProvider(),
        ).conversations.activities_client
        service_url = "https://override.service.url/"

        await activities_client.create(
            "test_conversation_id",
            mock_activity,
            service_url=service_url,
            agent_user=identity,
        )
        assert (
            str(request_capture._capture.last_request.url)
            == "https://override.service.url/v3/conversations/test_conversation_id/activities"
        )
        assert "authorization" in request_capture._capture.last_request.headers

        await activities_client.update(
            "test_conversation_id",
            "activity-id",
            mock_activity,
            service_url=service_url,
            agent_user=identity,
        )
        assert (
            str(request_capture._capture.last_request.url)
            == "https://override.service.url/v3/conversations/test_conversation_id/activities/activity-id"
        )
        assert "authorization" in request_capture._capture.last_request.headers

        await activities_client.reply(
            "test_conversation_id",
            "activity-id",
            mock_activity,
            service_url=service_url,
            agent_user=identity,
        )
        assert (
            str(request_capture._capture.last_request.url)
            == "https://override.service.url/v3/conversations/test_conversation_id/activities/activity-id"
        )
        assert "authorization" in request_capture._capture.last_request.headers

        await activities_client.delete(
            "test_conversation_id",
            "activity-id",
            service_url=service_url,
            agent_user=identity,
        )
        assert (
            str(request_capture._capture.last_request.url)
            == "https://override.service.url/v3/conversations/test_conversation_id/activities/activity-id"
        )
        assert "authorization" in request_capture._capture.last_request.headers

        await activities_client.get_members(
            "test_conversation_id",
            "activity-id",
            service_url=service_url,
            agent_user=identity,
        )
        assert (
            str(request_capture._capture.last_request.url)
            == "https://override.service.url/v3/conversations/test_conversation_id/activities/activity-id/members"
        )
        assert "authorization" in request_capture._capture.last_request.headers
        assert calls == [(None, identity)] * 5

    async def test_grouped_activity_methods_accept_service_url_kwarg(self, request_capture, mock_activity):
        client = ConversationClient("https://default.service.url", request_capture)
        activities = client.activities("test_conversation_id")
        service_url = "https://override.service.url/"

        await activities.create(mock_activity, service_url=service_url)
        assert (
            str(request_capture._capture.last_request.url)
            == "https://override.service.url/v3/conversations/test_conversation_id/activities"
        )

        await activities.update("activity-id", mock_activity, service_url=service_url)
        assert (
            str(request_capture._capture.last_request.url)
            == "https://override.service.url/v3/conversations/test_conversation_id/activities/activity-id"
        )

        await activities.reply("activity-id", mock_activity, service_url=service_url)
        assert (
            str(request_capture._capture.last_request.url)
            == "https://override.service.url/v3/conversations/test_conversation_id/activities/activity-id"
        )

        await activities.delete("activity-id", service_url=service_url)
        assert (
            str(request_capture._capture.last_request.url)
            == "https://override.service.url/v3/conversations/test_conversation_id/activities/activity-id"
        )

        await activities.get_members("activity-id", service_url=service_url)
        assert (
            str(request_capture._capture.last_request.url)
            == "https://override.service.url/v3/conversations/test_conversation_id/activities/activity-id/members"
        )

        await activities.create_targeted(mock_activity, service_url=service_url)
        assert (
            str(request_capture._capture.last_request.url)
            == "https://override.service.url/v3/conversations/test_conversation_id/activities?isTargetedActivity=true"
        )

        await activities.update_targeted("activity-id", mock_activity, service_url=service_url)
        assert (
            str(request_capture._capture.last_request.url)
            == "https://override.service.url/v3/conversations/test_conversation_id/activities/activity-id"
            "?isTargetedActivity=true"
        )

        await activities.delete_targeted("activity-id", service_url=service_url)
        assert (
            str(request_capture._capture.last_request.url)
            == "https://override.service.url/v3/conversations/test_conversation_id/activities/activity-id"
            "?isTargetedActivity=true"
        )

    async def test_activity_create_agent_user_without_auth_provider_uses_http_client_auth(
        self, request_capture, mock_activity
    ):
        """Test agent user without an auth provider leaves auth resolution to the HTTP client."""
        identity = AgentUser("agent-app-instance-id", "agent-user-id", tenant_id="tenant-id")
        client = ApiClient("https://test.service.url", request_capture).from_agent_user(identity).conversations

        await client.activities("test_conversation_id").create(mock_activity)

        last_request = request_capture._capture.last_request
        assert "authorization" not in last_request.headers

    async def test_activity_create_records_diagnostics(self, request_capture, mock_activity):
        tracer = RecordingTracer()
        client = ConversationClient("https://test.service.url/", request_capture)

        with (
            patch("microsoft_teams.api.diagnostics._outbound.get_tracer", return_value=tracer),
            patch("microsoft_teams.api.diagnostics._outbound.record_outbound_call") as record_outbound_call,
            patch("microsoft_teams.api.diagnostics._outbound.record_outbound_error") as record_outbound_error,
        ):
            result = await client.create_activity("conv-1", mock_activity)

        assert result.id == "mock_conversation_id"
        record_outbound_call.assert_called_once_with("create")
        record_outbound_error.assert_not_called()
        assert len(tracer.spans) == 1
        span = tracer.spans[0]
        assert span.name == "microsoft.teams.api.client"
        assert span.options == {
            "kind": SpanKind.CLIENT,
            "record_exception": False,
            "set_status_on_exception": False,
        }
        assert span.attributes == {
            "operation": "create",
            "service.url": "https://test.service.url",
            "conversation.id": "conv-1",
            "activity.type": "message",
            "activity.id": "mock_conversation_id",
        }

    async def test_request_without_metadata_does_not_record_api_client_telemetry(self, request_capture):
        tracer = RecordingTracer()
        api_client = ApiClient("https://test.service.url", request_capture)

        with (
            patch("microsoft_teams.api.diagnostics._outbound.get_tracer", return_value=tracer),
            patch("microsoft_teams.api.diagnostics._outbound.record_outbound_call") as record_outbound_call,
            patch("microsoft_teams.api.diagnostics._outbound.record_outbound_error") as record_outbound_error,
        ):
            await api_client.http.post("https://test.service.url/v3/conversations", json={"ok": True})

        assert tracer.spans == []
        record_outbound_call.assert_not_called()
        record_outbound_error.assert_not_called()

    async def test_api_client_middleware_uses_supplied_attributes_without_deriving_semantics(self, request_capture):
        tracer = RecordingTracer()
        api_client = ApiClient("https://test.service.url", request_capture)
        attributes = {
            "operation": "create",
            "custom.attribute": "custom-value",
        }

        with patch("microsoft_teams.api.diagnostics._outbound.get_tracer", return_value=tracer):
            await api_client.http.post(
                "https://test.service.url/v3/conversations/conv-1/activities",
                json={"ok": True},
                _metadata=ApiOutboundTelemetryMetadata(operation="create", attributes=attributes),
            )

        assert len(tracer.spans) == 1
        assert tracer.spans[0].attributes == attributes

    async def test_api_client_middleware_invokes_response_hook(self):
        tracer = RecordingTracer()
        hook_responses: list[httpx.Response] = []
        http_client = Client(ClientOptions(base_url="https://test.service.url"))

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"id": "response-id"}, headers={"content-type": "application/json"})

        http_client.http._transport = httpx.MockTransport(handler)
        api_client = ApiClient("https://test.service.url", http_client)

        async def on_response(span: Span, response: httpx.Response) -> None:
            hook_responses.append(response)
            span.set_attribute("hook.attribute", str(response.json()["id"]))

        with patch("microsoft_teams.api.diagnostics._outbound.get_tracer", return_value=tracer):
            await api_client.http.post(
                "/v3/conversations/conv-1/activities",
                json={"ok": True},
                _metadata=ApiOutboundTelemetryMetadata(
                    operation="create",
                    attributes={"operation": "create"},
                    on_response=on_response,
                ),
            )

        assert len(hook_responses) == 1
        assert tracer.spans[0].attributes == {
            "operation": "create",
            "hook.attribute": "response-id",
        }
        assert tracer.spans[0].ended_count == 1

    async def test_api_client_middleware_swallows_response_hook_failure(self):
        tracer = RecordingTracer()
        http_client = Client(ClientOptions(base_url="https://test.service.url"))
        response = httpx.Response(200, json={"id": "response-id"}, headers={"content-type": "application/json"})

        def handler(request: httpx.Request) -> httpx.Response:
            return response

        http_client.http._transport = httpx.MockTransport(handler)
        api_client = ApiClient("https://test.service.url", http_client)

        async def on_response(span: Span, response: httpx.Response) -> None:
            raise RuntimeError("hook failed")

        with (
            patch("microsoft_teams.api.diagnostics._outbound.get_tracer", return_value=tracer),
            patch("microsoft_teams.api.diagnostics._outbound.record_exception") as record_exception,
            patch("microsoft_teams.api.diagnostics._outbound.record_outbound_error") as record_outbound_error,
            patch("microsoft_teams.api.diagnostics._outbound.logger.warning") as warning,
        ):
            result = await api_client.http.post(
                "/v3/conversations/conv-1/activities",
                json={"ok": True},
                _metadata=ApiOutboundTelemetryMetadata(
                    operation="create",
                    attributes={"operation": "create"},
                    on_response=on_response,
                ),
            )

        assert result is response
        assert len(tracer.spans) == 1
        assert tracer.spans[0].attributes == {"operation": "create"}
        assert tracer.spans[0].ended_count == 1
        record_exception.assert_not_called()
        record_outbound_error.assert_not_called()
        warning.assert_called_once()

    async def test_activity_send_paths_set_response_activity_id_from_client_owned_hooks(
        self, request_capture, mock_activity
    ):
        tracer = RecordingTracer()
        client = ConversationClient("https://test.service.url", request_capture)

        with patch("microsoft_teams.api.diagnostics._outbound.get_tracer", return_value=tracer):
            await client.create_activity("conv-1", mock_activity)
            await client.update_activity("conv-1", "act-1", mock_activity)
            await client.reply_to_activity("conv-1", "act-1", mock_activity)
            await client.create_targeted_activity("conv-1", mock_activity)
            await client.update_targeted_activity("conv-1", "act-1", mock_activity)

        assert [span.attributes["activity.id"] for span in tracer.spans] == [
            "mock_conversation_id",
            "mock_activity_id",
            "mock_conversation_id",
            "mock_conversation_id",
            "mock_activity_id",
        ]

    async def test_activity_create_nests_auth_outbound_under_api_outbound_span(self, request_capture, mock_activity):
        tracer = RecordingTracer()
        calls = []

        class TestAuthProvider:
            def token(self, *, scope=None, agent_user=None):
                calls.append((scope, agent_user))
                return "bot-token"

        client = ApiClient("https://test.service.url", request_capture, auth_provider=TestAuthProvider()).conversations

        with (
            patch("microsoft_teams.api.diagnostics._outbound.get_tracer", return_value=tracer),
            patch("microsoft_teams.api.clients.api_client.get_tracer", return_value=tracer),
        ):
            await client.create_activity("conv-1", mock_activity)

        assert calls == [(None, None)]
        assert [span.name for span in tracer.spans[:2]] == [
            "microsoft.teams.api.client",
            "microsoft.teams.auth.outbound",
        ]

    async def test_activity_create_auth_failure_records_api_client_error(self, request_capture, mock_activity):
        tracer = RecordingTracer()
        error = RuntimeError("token failure")

        class TestAuthProvider:
            def token(self, *, scope=None, agent_user=None):
                raise error

        client = ApiClient("https://test.service.url", request_capture, auth_provider=TestAuthProvider()).conversations

        with (
            patch("microsoft_teams.api.diagnostics._outbound.get_tracer", return_value=tracer),
            patch("microsoft_teams.api.clients.api_client.get_tracer", return_value=tracer),
            patch("microsoft_teams.api.diagnostics._outbound.record_outbound_call") as record_outbound_call,
            patch("microsoft_teams.api.diagnostics._outbound.record_outbound_error") as record_outbound_error,
            patch("microsoft_teams.api.diagnostics._outbound.record_exception") as record_outbound_exception,
            patch("microsoft_teams.api.clients.api_client.record_exception"),
            pytest.raises(RuntimeError, match="token failure"),
        ):
            await client.create_activity("conv-1", mock_activity)

        assert [span.name for span in tracer.spans[:2]] == [
            "microsoft.teams.api.client",
            "microsoft.teams.auth.outbound",
        ]
        record_outbound_call.assert_called_once_with("create")
        record_outbound_error.assert_called_once_with("create")
        record_outbound_exception.assert_called_once_with(tracer.spans[0], error)

    async def test_request_authorization_header_bypasses_auth_provider_with_metadata(self, request_capture):
        calls = []

        class TestAuthProvider:
            def token(self, *, scope=None, agent_user=None):
                calls.append((scope, agent_user))
                return "bot-token"

        api_client = ApiClient("https://test.service.url", request_capture, auth_provider=TestAuthProvider())

        await api_client.http.post(
            "https://test.service.url/v3/conversations",
            headers={"Authorization": "******"},
            json={"ok": True},
            _metadata=ApiOutboundTelemetryMetadata(operation="create"),
        )

        assert calls == []
        request = request_capture._capture.last_request
        assert request.headers["authorization"] == "******"

    async def test_activity_create_records_diagnostics_on_error(self, mock_http_client, mock_activity):
        tracer = RecordingTracer()
        error = RuntimeError("send failed")

        def handler(request: httpx.Request) -> httpx.Response:
            raise error

        http_client = Client(ClientOptions(base_url="https://mock.api.com"))
        http_client.http._transport = httpx.MockTransport(handler)
        client = ConversationClient("https://test.service.url", http_client)

        with (
            patch("microsoft_teams.api.diagnostics._outbound.get_tracer", return_value=tracer),
            patch("microsoft_teams.api.diagnostics._outbound.record_outbound_call") as record_outbound_call,
            patch("microsoft_teams.api.diagnostics._outbound.record_outbound_error") as record_outbound_error,
            patch("microsoft_teams.api.diagnostics._outbound.record_exception") as record_exception,
            pytest.raises(RuntimeError, match="send failed"),
        ):
            await client.create_activity("conv-1", mock_activity)

        record_outbound_call.assert_called_once_with("create")
        record_outbound_error.assert_called_once_with("create")
        record_exception.assert_called_once_with(tracer.spans[0], error)

    async def test_targeted_activity_operations_record_diagnostics_operations(self, mock_http_client, mock_activity):
        client = ConversationClient("https://test.service.url", mock_http_client)

        with patch("microsoft_teams.api.diagnostics._outbound.record_outbound_call") as record_outbound_call:
            await client.create_targeted_activity("conv-1", mock_activity)
            await client.update_targeted_activity("conv-1", "act-1", mock_activity)
            await client.delete_targeted_activity("conv-1", "act-1")

        assert record_outbound_call.call_args_list == [
            call("create_targeted"),
            call("update_targeted"),
            call("delete_targeted"),
        ]

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
        payload = json.loads(last_request.content)
        assert payload["type"] == "message"

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

        # Validate request payload - check that replyToId was added
        payload = json.loads(last_request.content)
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
        assert result[0].aad_object_id == "mock_aad_object_id"

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
        assert result.aad_object_id == "mock_aad_object_id"

        # Validate request details
        last_request = request_capture._capture.last_request
        assert last_request.method == "GET"
        assert (
            str(last_request.url) == f"https://test.service.url/v3/conversations/{conversation_id}/members/{member_id}"
        )

    async def test_member_operations_use_scoped_service_url(self, request_capture):
        client = (
            ApiClient("https://test.service.url", request_capture)
            .from_service_url("https://override.service.url/")
            .conversations
        )
        members = client.members("test_conversation_id")

        await members.get_all()
        await members.get("test_member_id")
        await members.get_paged(page_size=10)

        urls = [str(request.url) for request in request_capture._capture.requests[-3:]]
        assert urls == [
            "https://override.service.url/v3/conversations/test_conversation_id/members",
            "https://override.service.url/v3/conversations/test_conversation_id/members/test_member_id",
            "https://override.service.url/v3/conversations/test_conversation_id/pagedMembers?pageSize=10",
        ]

    async def test_member_operations_use_auth_provider_for_bot_token(self, request_capture):
        calls = []

        class TestAuthProvider:
            def token(self, *, scope=None, agent_user=None):
                calls.append((scope, agent_user))
                return "bot-token"

        client = ApiClient("https://test.service.url", request_capture, auth_provider=TestAuthProvider()).conversations
        members = client.members("test_conversation_id")

        await members.get_all()
        await members.get("test_member_id")
        await members.get_paged(page_size=10)

        assert calls == [
            (None, None),
            (None, None),
            (None, None),
        ]
        for request in request_capture._capture.requests[-3:]:
            assert request.headers["authorization"] == "Bearer bot-token"

    async def test_member_operations_use_agent_user(self, request_capture):
        calls = []

        class TestAuthProvider:
            def token(self, *, scope=None, agent_user=None):
                calls.append((scope, agent_user))
                return "agent-user-token"

        identity = AgentUser("agent-app-instance-id", "agent-user-id", tenant_id="tenant-id")
        client = ApiClient(
            "https://test.service.url", request_capture, auth_provider=TestAuthProvider(), agent_user=identity
        ).conversations
        members = client.members("test_conversation_id")

        await members.get_all()
        await members.get("test_member_id")
        await members.get_paged(page_size=10)

        assert calls == [
            (None, identity),
            (None, identity),
            (None, identity),
        ]
        for request in request_capture._capture.requests[-3:]:
            assert request.headers["authorization"] == "Bearer agent-user-token"

    async def test_member_get_paged(self, mock_http_client):
        """Test getting a page of members returns PagedMembersResult."""

        service_url = "https://test.service.url"
        client = ConversationClient(service_url, mock_http_client)

        conversation_id = "test_conversation_id"
        members = client.members(conversation_id)

        result = await members.get_paged()

        assert isinstance(result, PagedMembersResult)
        assert len(result.members) == 1
        assert isinstance(result.members[0], TeamsChannelAccount)
        assert result.members[0].id == "mock_member_id"
        assert result.continuation_token == "mock_continuation_token"

    async def test_member_get_paged_with_token(self, mock_http_client):
        """Test get_paged passes continuation_token and page_size."""

        service_url = "https://test.service.url"
        client = ConversationClient(service_url, mock_http_client)
        members = client.members("test_conversation_id")

        mock_response = httpx.Response(
            200,
            json={"members": [], "continuationToken": None},
            headers={"content-type": "application/json"},
        )
        with patch.object(mock_http_client, "get", new_callable=AsyncMock, return_value=mock_response) as mock_get:
            await members.get_paged(page_size=50, continuation_token="some_token")

        called_params = mock_get.call_args.kwargs.get("params", {})
        assert called_params.get("pageSize") == 50
        assert called_params.get("continuationToken") == "some_token"


@pytest.mark.unit
class TestConversationClientHttpClientSharing:
    """Test that HTTP client is properly shared between sub-clients."""

    def test_http_client_sharing(self, mock_http_client):
        """Test that all sub-clients share the same HTTP client."""
        service_url = "https://test.service.url"
        client = ConversationClient(service_url, mock_http_client)

        assert client.activities_client.http == mock_http_client
        assert client.members_client.http == mock_http_client
        assert client._reactions_client.http == mock_http_client

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
        assert client._reactions_client.http == new_http_client


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


@pytest.mark.unit
@pytest.mark.asyncio
class TestConversationClientFlattened:
    """Unit tests for the flattened ConversationClient methods (conversations.create_activity, etc.)."""

    async def test_create_activity(self, request_capture, mock_activity):
        """create_activity should POST an activity."""
        client = ConversationClient("https://test.service.url", request_capture)

        result = await client.create_activity("conv-1", mock_activity)

        assert result is not None
        assert result.id is not None
        last_request = request_capture._capture.last_request
        assert last_request.method == "POST"
        assert str(last_request.url) == "https://test.service.url/v3/conversations/conv-1/activities"

    async def test_update_activity(self, request_capture, mock_activity):
        """update_activity should PUT an activity."""
        client = ConversationClient("https://test.service.url", request_capture)

        result = await client.update_activity("conv-1", "act-1", mock_activity)

        assert result is not None
        last_request = request_capture._capture.last_request
        assert last_request.method == "PUT"
        assert str(last_request.url) == "https://test.service.url/v3/conversations/conv-1/activities/act-1"

    async def test_reply_to_activity(self, request_capture, mock_activity):
        """reply_to_activity should POST a reply with replyToId set."""
        client = ConversationClient("https://test.service.url", request_capture)

        result = await client.reply_to_activity("conv-1", "act-1", mock_activity)

        assert result is not None
        last_request = request_capture._capture.last_request
        assert last_request.method == "POST"
        assert str(last_request.url) == "https://test.service.url/v3/conversations/conv-1/activities/act-1"
        payload = json.loads(last_request.content)
        assert payload["replyToId"] == "act-1"

    async def test_delete_activity(self, request_capture):
        """delete_activity should DELETE an activity."""
        client = ConversationClient("https://test.service.url", request_capture)

        await client.delete_activity("conv-1", "act-1")

        last_request = request_capture._capture.last_request
        assert last_request.method == "DELETE"
        assert str(last_request.url) == "https://test.service.url/v3/conversations/conv-1/activities/act-1"

    async def test_get_activity_members(self, request_capture):
        """get_activity_members should GET the activity members."""
        client = ConversationClient("https://test.service.url", request_capture)

        result = await client.get_activity_members("conv-1", "act-1")

        assert isinstance(result, list)
        last_request = request_capture._capture.last_request
        assert last_request.method == "GET"
        assert str(last_request.url) == "https://test.service.url/v3/conversations/conv-1/activities/act-1/members"

    async def test_get_members(self, request_capture):
        """get_members should GET all conversation members."""
        client = ConversationClient("https://test.service.url", request_capture)

        result = await client.get_members("conv-1")

        assert isinstance(result, list)
        assert result[0].id == "mock_member_id"
        last_request = request_capture._capture.last_request
        assert last_request.method == "GET"
        assert str(last_request.url) == "https://test.service.url/v3/conversations/conv-1/members"

    async def test_get_member_by_id(self, request_capture):
        """get_member_by_id should GET a single conversation member."""
        client = ConversationClient("https://test.service.url", request_capture)

        result = await client.get_member_by_id("conv-1", "member-1")

        assert result.id == "mock_member_id"
        last_request = request_capture._capture.last_request
        assert last_request.method == "GET"
        assert str(last_request.url) == "https://test.service.url/v3/conversations/conv-1/members/member-1"

    async def test_get_paged_members(self, mock_http_client):
        """get_paged_members should return a PagedMembersResult."""
        client = ConversationClient("https://test.service.url", mock_http_client)

        result = await client.get_paged_members("conv-1")

        assert isinstance(result, PagedMembersResult)
        assert result.members[0].id == "mock_member_id"
        assert result.continuation_token == "mock_continuation_token"

    async def test_create_targeted_activity(self, mock_http_client, mock_activity):
        """create_targeted_activity should return a SentActivity."""
        client = ConversationClient("https://test.service.url", mock_http_client)

        result = await client.create_targeted_activity("conv-1", mock_activity)

        assert result is not None

    async def test_update_targeted_activity(self, mock_http_client, mock_activity):
        """update_targeted_activity should return a SentActivity."""
        client = ConversationClient("https://test.service.url", mock_http_client)

        result = await client.update_targeted_activity("conv-1", "act-1", mock_activity)

        assert result is not None

    async def test_delete_targeted_activity(self, mock_http_client):
        """delete_targeted_activity should not raise."""
        client = ConversationClient("https://test.service.url", mock_http_client)

        await client.delete_targeted_activity("conv-1", "act-1")

    async def test_add_reaction(self, mock_http_client):
        """add_reaction should PUT to the reactions endpoint."""
        client = ConversationClient("https://test.service.url", mock_http_client)

        with patch.object(mock_http_client, "put", new_callable=AsyncMock) as mock_put:
            await client.add_reaction("conv-1", "act-1", "like")

        expected_url = "https://test.service.url/v3/conversations/conv-1/activities/act-1/reactions/like"
        mock_put.assert_called_once_with(expected_url)

    async def test_delete_reaction(self, mock_http_client):
        """delete_reaction should DELETE from the reactions endpoint."""
        client = ConversationClient("https://test.service.url", mock_http_client)

        with patch.object(mock_http_client, "delete", new_callable=AsyncMock) as mock_delete:
            await client.delete_reaction("conv-1", "act-1", "like")

        expected_url = "https://test.service.url/v3/conversations/conv-1/activities/act-1/reactions/like"
        mock_delete.assert_called_once_with(expected_url)


@pytest.mark.unit
class TestConversationClientDeprecatedAccessors:
    """The grouped activities()/members() accessors are deprecated but still supported."""

    def test_activities_accessor_warns(self, mock_http_client):
        client = ConversationClient("https://test.service.url", mock_http_client)
        with pytest.warns(DeprecationWarning):
            client.activities("conv-1")

    def test_members_accessor_warns(self, mock_http_client):
        client = ConversationClient("https://test.service.url", mock_http_client)
        with pytest.warns(DeprecationWarning):
            client.members("conv-1")
