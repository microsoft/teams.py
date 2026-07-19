"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

from unittest.mock import MagicMock, patch

import microsoft_teams.apps as apps
from microsoft_teams.api import ActivityTypeAdapter
from microsoft_teams.apps import (
    TEAMS_BOT_APPLICATION_METER_NAME,
    TEAMS_BOT_APPLICATION_TRACER_NAME,
    ActivityContext,
    TeamsBaggageBuilder,
    TeamsBotApplicationTelemetry,
    with_teams_baggage,
)
from microsoft_teams.apps.diagnostics._helpers import (
    get_meter,
    get_tracer,
    record_activity_received,
    record_exception,
    record_handler_dispatched,
    record_handler_duration,
    record_handler_failure,
    record_handler_unmatched,
    record_oauth_error,
    record_oauth_operation,
    record_turn_duration,
)
from microsoft_teams.apps.events import CoreActivity
from opentelemetry import baggage
from opentelemetry import context as otel_context
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.trace import StatusCode


def test_public_telemetry_names_are_exported():
    assert TEAMS_BOT_APPLICATION_TRACER_NAME == "Microsoft.Teams.Apps"
    assert TEAMS_BOT_APPLICATION_METER_NAME == "Microsoft.Teams.Apps"
    assert TeamsBotApplicationTelemetry.tracer_name == "Microsoft.Teams.Apps"
    assert TeamsBotApplicationTelemetry.meter_name == "Microsoft.Teams.Apps"
    assert "TEAMS_BOT_APPLICATION_TRACER_NAME" in apps.__all__
    assert "TEAMS_BOT_APPLICATION_METER_NAME" in apps.__all__
    assert "TeamsBaggageBuilder" in apps.__all__
    assert "TeamsBotApplicationTelemetry" in apps.__all__
    assert "with_teams_baggage" in apps.__all__
    assert apps.TeamsBaggageBuilder is TeamsBaggageBuilder
    assert apps.with_teams_baggage is with_teams_baggage


def test_runtime_instrumentation_names_stay_internal():
    private_groups = [
        "APP_ATTRIBUTE_NAMES",
        "APP_BAGGAGE_KEYS",
        "APP_HANDLER_DISPATCHES",
        "APP_METRIC_NAMES",
        "APP_OAUTH_ERROR_TYPES",
        "APP_OAUTH_OPERATIONS",
        "APP_OAUTH_RESULTS",
        "APP_SPAN_NAMES",
    ]
    for group in private_groups:
        assert group not in apps.__all__
        assert not hasattr(apps, group)


def test_helpers_use_canonical_source_names():
    with patch("microsoft_teams.apps.diagnostics._helpers.trace.get_tracer") as mock_get_tracer:
        tracer = get_tracer()

    mock_get_tracer.assert_called_once_with("Microsoft.Teams.Apps")
    assert tracer is mock_get_tracer.return_value

    with patch("microsoft_teams.apps.diagnostics._helpers.metrics.get_meter") as mock_get_meter:
        meter = get_meter()

    mock_get_meter.assert_called_once_with("Microsoft.Teams.Apps")
    assert meter is mock_get_meter.return_value


def test_baggage_builder_typed_setters_attach_and_restore_context():
    token = otel_context.attach(baggage.set_baggage("service.name", "previous"))
    try:
        builder = (
            TeamsBaggageBuilder()
            .tenant_id("tenant-1")
            .conversation_id("conversation-1")
            .conversation_item_link("https://service.url")
            .channel_name("msteams")
            .channel_link("https://channel.url")
            .agent_id("agent-1")
            .agent_name("Agent")
            .agentic_user_id("agent-user-1")
            .agent_blueprint_id("blueprint-1")
            .user_name("User")
            .operation_source("service")
            .invoke_agent_server("server.example", 443)
            .user_id("user-aad-1")
            .user_email("user@example.com")
            .agent_description("assistant")
            .agentic_user_email("agent-user@example.com")
            .set("custom.key", " custom-value ")
            .set("blank.value", " ")
        )

        with builder.build():
            assert baggage.get_baggage("microsoft.tenant.id") == "tenant-1"
            assert baggage.get_baggage("gen_ai.conversation.id") == "conversation-1"
            assert baggage.get_baggage("microsoft.conversation.item.link") == "https://service.url"
            assert baggage.get_baggage("microsoft.channel.name") == "msteams"
            assert baggage.get_baggage("microsoft.channel.link") == "https://channel.url"
            assert baggage.get_baggage("gen_ai.agent.id") == "agent-1"
            assert baggage.get_baggage("gen_ai.agent.name") == "Agent"
            assert baggage.get_baggage("microsoft.agent.user.id") == "agent-user-1"
            assert baggage.get_baggage("microsoft.a365.agent.blueprint.id") == "blueprint-1"
            assert baggage.get_baggage("user.name") == "User"
            assert baggage.get_baggage("service.name") == "service"
            assert baggage.get_baggage("server.address") == "server.example"
            assert baggage.get_baggage("server.port") == "443"
            assert baggage.get_baggage("user.id") == "user-aad-1"
            assert baggage.get_baggage("user.email") == "user@example.com"
            assert baggage.get_baggage("gen_ai.agent.description") == "assistant"
            assert baggage.get_baggage("microsoft.agent.user.email") == "agent-user@example.com"
            assert baggage.get_baggage("custom.key") == "custom-value"
            assert baggage.get_baggage("blank.value") is None

        assert baggage.get_baggage("service.name") == "previous"
        assert baggage.get_baggage("server.address") is None
    finally:
        otel_context.detach(token)


def test_baggage_builder_from_activity_extracts_agent365_keys():
    core_activity = CoreActivity(
        type="message",
        id="activity-1",
        service_url="https://service.url",
        **{
            "from": {
                "id": "caller-1",
                "aadObjectId": "caller-aad-1",
                "name": "Caller",
                "email": "caller@example.com",
            },
            "conversation": {"id": "conversation-1"},
            "recipient": {
                "id": "bot-1",
                "name": "Agent",
                "email": "agentic-user@example.com",
                "tenantId": "recipient-tenant",
                "agenticAppId": "agent-app-1",
                "agenticUserId": "agent-user-1",
                "agenticAppBlueprintId": "blueprint-1",
                "userRole": "assistant",
            },
            "channelId": "msteams",
            "channelData": {"tenant": {"id": "channel-tenant"}},
        },
    )
    activity = ActivityTypeAdapter.validate_python(core_activity.model_dump(by_alias=True, exclude_none=True))
    ctx = MagicMock(spec=ActivityContext)
    ctx.activity = activity

    def configure_service(builder: TeamsBaggageBuilder) -> None:
        builder.operation_source("service")

    with with_teams_baggage(ctx, configure_service):
        assert baggage.get_baggage("microsoft.tenant.id") == "recipient-tenant"
        assert baggage.get_baggage("gen_ai.conversation.id") == "conversation-1"
        assert baggage.get_baggage("microsoft.conversation.item.link") == "https://service.url"
        assert baggage.get_baggage("microsoft.channel.name") == "msteams"
        assert baggage.get_baggage("microsoft.channel.link") is None
        assert baggage.get_baggage("user.id") == "caller-aad-1"
        assert baggage.get_baggage("user.name") == "Caller"
        assert baggage.get_baggage("user.email") == "caller@example.com"
        assert baggage.get_baggage("gen_ai.agent.id") == "agent-app-1"
        assert baggage.get_baggage("gen_ai.agent.name") == "Agent"
        assert baggage.get_baggage("microsoft.agent.user.id") == "agent-user-1"
        assert baggage.get_baggage("microsoft.agent.user.email") == "agentic-user@example.com"
        assert baggage.get_baggage("gen_ai.agent.description") == "assistant"
        assert baggage.get_baggage("microsoft.a365.agent.blueprint.id") == "blueprint-1"
        assert baggage.get_baggage("service.name") == "service"


def test_with_teams_baggage_supports_configure_without_source():
    def configure_service(builder: TeamsBaggageBuilder) -> None:
        builder.operation_source("service")

    with with_teams_baggage(configure=configure_service):
        assert baggage.get_baggage("service.name") == "service"

    assert baggage.get_baggage("service.name") is None


def test_baggage_builder_from_activity_falls_back_to_channel_tenant_and_bot_id():
    core_activity = CoreActivity(
        type="message",
        id="activity-1",
        **{
            "from": {"id": "caller-1"},
            "conversation": {"id": "conversation-1"},
            "recipient": {"id": "bot-1"},
            "channelId": "msteams",
            "channelData": {"tenant": {"id": "channel-tenant"}},
        },
    )
    activity = ActivityTypeAdapter.validate_python(core_activity.model_dump(by_alias=True, exclude_none=True))

    with TeamsBaggageBuilder.from_activity(activity).build():
        assert baggage.get_baggage("microsoft.tenant.id") == "channel-tenant"
        assert baggage.get_baggage("gen_ai.agent.id") == "bot-1"
        assert baggage.get_baggage("user.id") is None
        assert baggage.get_baggage("user.email") is None


def test_app_metrics_are_recorded_with_allowed_attributes():
    metric_reader = InMemoryMetricReader()
    meter_provider = MeterProvider(metric_readers=[metric_reader])
    meter = meter_provider.get_meter("Microsoft.Teams.Apps")

    with patch("microsoft_teams.apps.diagnostics._helpers.get_meter", return_value=meter):
        record_activity_received("message")
        record_turn_duration(5.5, "message")
        record_handler_dispatched("message", "type")
        record_handler_duration(2.5, "message", "type")
        record_handler_failure("message", "type")
        record_handler_unmatched("invoke", "composeExtension/query")
        record_oauth_operation("test-connection", "token_exchange", "success", 3.5)
        record_oauth_error("test-connection", "token_exchange", "http_error")

    metrics = {}
    metrics_data = metric_reader.get_metrics_data()
    assert metrics_data is not None
    for resource_metric in metrics_data.resource_metrics:
        for scope_metric in resource_metric.scope_metrics:
            for metric in scope_metric.metrics:
                metrics[metric.name] = metric

    activities_point = metrics["microsoft.teams.activities.received"].data.data_points[0]
    assert activities_point.value == 1
    assert activities_point.attributes == {"activity.type": "message"}

    turn_duration_point = metrics["microsoft.teams.activity.process.duration"].data.data_points[0]
    assert turn_duration_point.sum == 5.5
    assert turn_duration_point.attributes == {"activity.type": "message"}

    dispatched_point = metrics["microsoft.teams.handler.dispatched"].data.data_points[0]
    assert dispatched_point.value == 1
    assert dispatched_point.attributes == {"handler.type": "message", "handler.dispatch": "type"}

    handler_duration_point = metrics["microsoft.teams.handler.duration"].data.data_points[0]
    assert handler_duration_point.sum == 2.5
    assert handler_duration_point.attributes == {"handler.type": "message", "handler.dispatch": "type"}

    failures_point = metrics["microsoft.teams.handler.failures"].data.data_points[0]
    assert failures_point.value == 1
    assert failures_point.attributes == {"handler.type": "message", "handler.dispatch": "type"}

    unmatched_point = metrics["microsoft.teams.handler.unmatched"].data.data_points[0]
    assert unmatched_point.value == 1
    assert unmatched_point.attributes == {"activity.type": "invoke", "invoke.name": "composeExtension/query"}

    oauth_operations_point = metrics["microsoft.teams.oauth.operations"].data.data_points[0]
    assert oauth_operations_point.value == 1
    assert oauth_operations_point.attributes == {
        "oauth.connection": "test-connection",
        "oauth.operation": "token_exchange",
        "oauth.result": "success",
    }

    oauth_duration_point = metrics["microsoft.teams.oauth.operation.duration"].data.data_points[0]
    assert oauth_duration_point.sum == 3.5
    assert oauth_duration_point.attributes == {
        "oauth.connection": "test-connection",
        "oauth.operation": "token_exchange",
        "oauth.result": "success",
    }

    oauth_errors_point = metrics["microsoft.teams.oauth.errors"].data.data_points[0]
    assert oauth_errors_point.value == 1
    assert oauth_errors_point.attributes == {
        "oauth.connection": "test-connection",
        "oauth.operation": "token_exchange",
        "oauth.error.type": "http_error",
    }
    meter_provider.shutdown()


def test_record_exception_marks_span_error():
    span = MagicMock()
    exception = RuntimeError("boom")

    record_exception(span, exception)

    span.record_exception.assert_called_once_with(exception)
    status = span.set_status.call_args.args[0]
    assert status.status_code == StatusCode.ERROR
    assert status.description == "boom"
