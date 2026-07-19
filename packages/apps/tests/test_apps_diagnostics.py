"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

from unittest.mock import MagicMock, patch

import microsoft_teams.apps as apps
from microsoft_teams.apps import (
    TEAMS_BOT_APPLICATION_METER_NAME,
    TEAMS_BOT_APPLICATION_TRACER_NAME,
    TeamsBotApplicationTelemetry,
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
    record_turn_duration,
)
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
    assert "TeamsBotApplicationTelemetry" in apps.__all__


def test_runtime_instrumentation_names_stay_internal():
    private_groups = [
        "APP_ATTRIBUTE_NAMES",
        "APP_HANDLER_DISPATCHES",
        "APP_METRIC_NAMES",
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


def test_app_metrics_are_recorded_with_allowed_attributes():
    metric_reader = InMemoryMetricReader()
    meter_provider = MeterProvider(metric_readers=[metric_reader])
    meter = meter_provider.get_meter("Microsoft.Teams.Apps")

    with patch("microsoft_teams.apps.diagnostics._helpers.get_meter", return_value=meter):
        record_activity_received("message")
        record_turn_duration(5.5, "message")
        record_handler_dispatched("message", "route")
        record_handler_duration(2.5, "message", "route")
        record_handler_failure("message", "route")
        record_handler_unmatched("invoke", "composeExtension/query")

    metrics = {}
    metrics_data = metric_reader.get_metrics_data()
    assert metrics_data is not None
    for resource_metric in metrics_data.resource_metrics:
        for scope_metric in resource_metric.scope_metrics:
            for metric in scope_metric.metrics:
                metrics[metric.name] = metric

    activities_point = metrics["teams.activities.received"].data.data_points[0]
    assert activities_point.value == 1
    assert activities_point.attributes == {"activity.type": "message"}

    turn_duration_point = metrics["teams.turn.duration"].data.data_points[0]
    assert turn_duration_point.sum == 5.5
    assert turn_duration_point.attributes == {"activity.type": "message"}

    dispatched_point = metrics["teams.handler.dispatched"].data.data_points[0]
    assert dispatched_point.value == 1
    assert dispatched_point.attributes == {"handler.type": "message", "handler.dispatch": "route"}

    handler_duration_point = metrics["teams.handler.duration"].data.data_points[0]
    assert handler_duration_point.sum == 2.5
    assert handler_duration_point.attributes == {"handler.type": "message", "handler.dispatch": "route"}

    failures_point = metrics["teams.handler.failures"].data.data_points[0]
    assert failures_point.value == 1
    assert failures_point.attributes == {"handler.type": "message", "handler.dispatch": "route"}

    unmatched_point = metrics["teams.handler.unmatched"].data.data_points[0]
    assert unmatched_point.value == 1
    assert unmatched_point.attributes == {"activity.type": "invoke", "invoke.name": "composeExtension/query"}
    meter_provider.shutdown()


def test_record_exception_marks_span_error():
    span = MagicMock()
    exception = RuntimeError("boom")

    record_exception(span, exception)

    span.record_exception.assert_called_once_with(exception)
    status = span.set_status.call_args.args[0]
    assert status.status_code == StatusCode.ERROR
    assert status.description == "boom"
