"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

import importlib.metadata
from pathlib import Path
from unittest.mock import MagicMock, patch

import microsoft_teams.apps as apps
from microsoft_teams.api import ActivityTypeAdapter
from microsoft_teams.apps import (
    TEAMS_BOT_APPLICATION_METER_NAME,
    TEAMS_BOT_APPLICATION_TRACER_NAME,
    ActivityContext,
    Agent365Baggage,
    TeamsBotApplicationTelemetry,
    agent365_baggage,
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
    assert TeamsBotApplicationTelemetry.instrumentation_version == importlib.metadata.version("microsoft-teams-apps")
    assert "TEAMS_BOT_APPLICATION_TRACER_NAME" in apps.__all__
    assert "TEAMS_BOT_APPLICATION_METER_NAME" in apps.__all__
    assert "TeamsBotApplicationTelemetry" in apps.__all__
    assert "Agent365Baggage" in apps.__all__
    assert "agent365_baggage" in apps.__all__
    assert apps.Agent365Baggage is Agent365Baggage
    assert apps.agent365_baggage is agent365_baggage


def test_runtime_instrumentation_names_stay_internal():
    private_groups = [
        "APP_ATTRIBUTE_NAMES",
        "AGENT365_BAGGAGE_KEYS",
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

    mock_get_tracer.assert_called_once_with(
        "Microsoft.Teams.Apps",
        instrumenting_library_version=TeamsBotApplicationTelemetry.instrumentation_version,
    )
    assert tracer is mock_get_tracer.return_value

    with patch("microsoft_teams.apps.diagnostics._helpers.metrics.get_meter") as mock_get_meter:
        meter = get_meter()

    mock_get_meter.assert_called_once_with(
        "Microsoft.Teams.Apps",
        version=TeamsBotApplicationTelemetry.instrumentation_version,
    )
    assert meter is mock_get_meter.return_value


def test_agent365_baggage_maps_conservative_context_and_restores_prior_baggage():
    activity = _agent365_activity()
    token = otel_context.attach(baggage.set_baggage("microsoft.tenant.id", "previous-tenant"))
    try:
        with agent365_baggage(
            activity, operation_source="agent365-example", server_address="localhost", server_port=3978
        ):
            assert baggage.get_baggage("microsoft.tenant.id") == "tenant-1"
            assert baggage.get_baggage("gen_ai.conversation.id") == "conv-789"
            assert baggage.get_baggage("microsoft.channel.name") == "msteams"
            assert baggage.get_baggage("gen_ai.agent.id") == "agent-app-1"
            assert baggage.get_baggage("microsoft.agent.user.id") == "agent-user-1"
            assert baggage.get_baggage("microsoft.a365.agent.blueprint.id") == "blueprint-1"
            assert baggage.get_baggage("user.id") == "caller-aad-1"
            assert baggage.get_baggage("service.name") == "agent365-example"
            assert baggage.get_baggage("server.address") == "localhost"
            assert baggage.get_baggage("server.port") == "3978"

            assert baggage.get_baggage("user.name") is None
            assert baggage.get_baggage("user.email") is None
            assert baggage.get_baggage("gen_ai.agent.name") is None
            assert baggage.get_baggage("microsoft.agent.user.email") is None
            assert baggage.get_baggage("gen_ai.agent.description") is None
            assert baggage.get_baggage("message.text") is None
            assert baggage.get_baggage("content") is None

        assert baggage.get_baggage("microsoft.tenant.id") == "previous-tenant"
        assert baggage.get_baggage("gen_ai.conversation.id") is None
    finally:
        otel_context.detach(token)


def test_agent365_baggage_accepts_activity_context_and_optional_identity_details():
    activity = _agent365_activity()
    ctx = MagicMock(spec=ActivityContext)
    ctx.activity = activity

    with agent365_baggage(ctx, include_identity_details=True):
        assert baggage.get_baggage("user.name") == "Caller"
        assert baggage.get_baggage("user.email") == "caller@example.com"
        assert baggage.get_baggage("gen_ai.agent.name") == "Agent"
        assert baggage.get_baggage("microsoft.agent.user.email") == "agentic-user@example.com"
        assert baggage.get_baggage("gen_ai.agent.description") == "assistant"


def test_agent365_baggage_supports_manual_values_without_activity():
    with (
        Agent365Baggage()
        .operation_source("service")
        .invoke_agent_server("server.example", 443)
        .set("custom.key", " custom-value ")
    ):
        assert baggage.get_baggage("service.name") == "service"
        assert baggage.get_baggage("server.address") == "server.example"
        assert baggage.get_baggage("server.port") == "443"
        assert baggage.get_baggage("custom.key") == "custom-value"

    with agent365_baggage(values={"service.name": "manual-service"}):
        assert baggage.get_baggage("service.name") == "manual-service"

    assert baggage.get_baggage("service.name") is None


def test_sdk_source_does_not_import_microsoft_otel_or_agents_sdk():
    packages_dir = Path(__file__).parents[3] / "packages"
    forbidden_imports = (
        "microsoft.opentelemetry",
        "microsoft_opentelemetry",
        "microsoft.agents",
        "microsoft_agents",
    )

    for source_file in packages_dir.glob("*/src/**/*.py"):
        source = source_file.read_text()
        assert not any(forbidden in source for forbidden in forbidden_imports), source_file

    for pyproject_file in packages_dir.glob("*/pyproject.toml"):
        manifest = pyproject_file.read_text()
        assert "microsoft-opentelemetry" not in manifest
        assert "microsoft-agents" not in manifest


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


def _agent365_activity():
    core_activity = CoreActivity(
        type="message",
        id="activity-1",
        service_url="https://service.url",
        **{
            "text": "message content should not become baggage",
            "from": {
                "id": "user-123",
                "aadObjectId": "caller-aad-1",
                "name": "Caller",
                "email": "caller@example.com",
            },
            "conversation": {"id": "conv-789"},
            "recipient": {
                "id": "bot-456",
                "name": "Agent",
                "tenantId": "tenant-1",
                "agenticAppId": "agent-app-1",
                "agenticUserId": "agent-user-1",
                "agenticAppBlueprintId": "blueprint-1",
                "email": "agentic-user@example.com",
                "userRole": "assistant",
            },
            "channelId": "msteams",
        },
    )
    return ActivityTypeAdapter.validate_python(core_activity.model_dump(by_alias=True, exclude_none=True))
