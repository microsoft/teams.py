"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from opentelemetry import metrics, trace
from opentelemetry.metrics import Meter
from opentelemetry.trace import Span, Status, StatusCode, Tracer

from ._telemetry import TeamsBotApplicationTelemetry


def get_tracer() -> Tracer:
    return trace.get_tracer(TeamsBotApplicationTelemetry.tracer_name)


def get_meter() -> Meter:
    return metrics.get_meter(TeamsBotApplicationTelemetry.meter_name)


def record_exception(span: Span, exception: BaseException) -> None:
    span.record_exception(exception)
    span.set_status(Status(StatusCode.ERROR, str(exception)))
