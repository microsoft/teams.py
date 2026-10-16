"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

import importlib.metadata
from unittest.mock import MagicMock, patch

import httpx2
import microsoft_teams.api as api
import pytest
from microsoft_teams.api import TEAMS_API_METER_NAME, TEAMS_API_TRACER_NAME, TeamsApiTelemetry
from microsoft_teams.api.diagnostics._helpers import (
    get_meter,
    get_tracer,
    record_exception,
    record_outbound_call,
    record_outbound_error,
)
from microsoft_teams.api.diagnostics._outbound import ApiOutboundTelemetryMetadata, ApiOutboundTelemetryMiddleware
from microsoft_teams.common import Client
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.trace import StatusCode


def test_public_telemetry_names_are_exported():
    assert TEAMS_API_TRACER_NAME == "Microsoft.Teams.Api"
    assert TEAMS_API_METER_NAME == "Microsoft.Teams.Api"
    assert TeamsApiTelemetry.tracer_name == "Microsoft.Teams.Api"
    assert TeamsApiTelemetry.meter_name == "Microsoft.Teams.Api"
    assert TeamsApiTelemetry.instrumentation_version == importlib.metadata.version("microsoft-teams-api")
    assert "TEAMS_API_TRACER_NAME" in api.__all__
    assert "TEAMS_API_METER_NAME" in api.__all__
    assert "TeamsApiTelemetry" in api.__all__


def test_runtime_instrumentation_names_stay_internal():
    private_groups = [
        "API_ATTRIBUTE_NAMES",
        "API_AUTH_FLOWS",
        "API_METRIC_NAMES",
        "API_OUTBOUND_OPERATIONS",
        "API_SPAN_NAMES",
    ]
    for group in private_groups:
        assert group not in api.__all__
        assert not hasattr(api, group)


def test_helpers_use_canonical_source_names():
    with patch("microsoft_teams.api.diagnostics._helpers.trace.get_tracer") as mock_get_tracer:
        tracer = get_tracer()

    mock_get_tracer.assert_called_once_with(
        "Microsoft.Teams.Api",
        instrumenting_library_version=TeamsApiTelemetry.instrumentation_version,
    )
    assert tracer is mock_get_tracer.return_value

    with patch("microsoft_teams.api.diagnostics._helpers.metrics.get_meter") as mock_get_meter:
        meter = get_meter()

    mock_get_meter.assert_called_once_with(
        "Microsoft.Teams.Api",
        version=TeamsApiTelemetry.instrumentation_version,
    )
    assert meter is mock_get_meter.return_value


def test_outbound_metrics_are_recorded_with_operation_attribute():
    metric_reader = InMemoryMetricReader()
    meter_provider = MeterProvider(metric_readers=[metric_reader])
    meter = meter_provider.get_meter("Microsoft.Teams.Api")

    with patch("microsoft_teams.api.diagnostics._helpers.get_meter", return_value=meter):
        record_outbound_call("create")
        record_outbound_error("create")

    metrics = {}
    metrics_data = metric_reader.get_metrics_data()
    assert metrics_data is not None
    for resource_metric in metrics_data.resource_metrics:
        for scope_metric in resource_metric.scope_metrics:
            for metric in scope_metric.metrics:
                metrics[metric.name] = metric

    calls_point = metrics["microsoft.teams.outbound.calls"].data.data_points[0]
    errors_point = metrics["microsoft.teams.outbound.errors"].data.data_points[0]
    assert calls_point.value == 1
    assert calls_point.attributes == {"operation": "create"}
    assert errors_point.value == 1
    assert errors_point.attributes == {"operation": "create"}
    meter_provider.shutdown()


def test_record_exception_marks_span_error():
    span = MagicMock()
    exception = RuntimeError("boom")

    record_exception(span, exception)

    span.record_exception.assert_called_once_with(exception)
    status = span.set_status.call_args.args[0]
    assert status.status_code == StatusCode.ERROR
    assert status.description == "boom"


async def test_httpx2_status_error_records_outbound_span_and_metric():
    tracer = MagicMock()
    span = tracer.start_as_current_span.return_value.__enter__.return_value
    async with httpx2.AsyncClient(transport=httpx2.MockTransport(lambda _: httpx2.Response(503))) as raw:
        client = Client(_http=raw)
        client.use(ApiOutboundTelemetryMiddleware())
        with (
            patch("microsoft_teams.api.diagnostics._outbound.get_tracer", return_value=tracer),
            patch("microsoft_teams.api.diagnostics._outbound.record_outbound_call") as calls,
            patch("microsoft_teams.api.diagnostics._outbound.record_outbound_error") as errors,
            pytest.raises(httpx2.HTTPStatusError) as raised,
        ):
            await client.get("https://example.test/send", _metadata=ApiOutboundTelemetryMetadata("create"))
    calls.assert_called_once_with("create")
    errors.assert_called_once_with("create")
    span.record_exception.assert_called_once_with(raised.value)
    assert span.set_status.call_args.args[0].status_code == StatusCode.ERROR
