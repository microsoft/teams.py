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
from microsoft_teams.apps.diagnostics._helpers import get_meter, get_tracer, record_exception
from opentelemetry.trace import StatusCode


def test_public_telemetry_names_are_exported():
    assert TEAMS_BOT_APPLICATION_TRACER_NAME == "Microsoft.Teams.Apps"
    assert TEAMS_BOT_APPLICATION_METER_NAME == "Microsoft.Teams.Apps"
    assert TeamsBotApplicationTelemetry.tracer_name == "Microsoft.Teams.Apps"
    assert TeamsBotApplicationTelemetry.meter_name == "Microsoft.Teams.Apps"
    assert "TEAMS_BOT_APPLICATION_TRACER_NAME" in apps.__all__
    assert "TEAMS_BOT_APPLICATION_METER_NAME" in apps.__all__
    assert "TeamsBotApplicationTelemetry" in apps.__all__


def test_helpers_use_canonical_source_names():
    with patch("microsoft_teams.apps.diagnostics._helpers.trace.get_tracer") as mock_get_tracer:
        tracer = get_tracer()

    mock_get_tracer.assert_called_once_with("Microsoft.Teams.Apps")
    assert tracer is mock_get_tracer.return_value

    with patch("microsoft_teams.apps.diagnostics._helpers.metrics.get_meter") as mock_get_meter:
        meter = get_meter()

    mock_get_meter.assert_called_once_with("Microsoft.Teams.Apps")
    assert meter is mock_get_meter.return_value


def test_record_exception_marks_span_error():
    span = MagicMock()
    exception = RuntimeError("boom")

    record_exception(span, exception)

    span.record_exception.assert_called_once_with(exception)
    status = span.set_status.call_args.args[0]
    assert status.status_code == StatusCode.ERROR
    assert status.description == "boom"
