"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from opentelemetry import metrics, trace
from opentelemetry.metrics import Counter, Meter
from opentelemetry.trace import Span, Status, StatusCode, Tracer

from ._constants import API_ATTRIBUTE_NAMES, API_METRIC_NAMES
from ._telemetry import TeamsApiTelemetry


def get_tracer() -> Tracer:
    return trace.get_tracer(TeamsApiTelemetry.tracer_name)


def get_meter() -> Meter:
    return metrics.get_meter(TeamsApiTelemetry.meter_name)


def get_outbound_calls_counter() -> Counter:
    return get_meter().create_counter(API_METRIC_NAMES.outbound_calls)


def get_outbound_errors_counter() -> Counter:
    return get_meter().create_counter(API_METRIC_NAMES.outbound_errors)


def record_outbound_call(operation: str) -> None:
    get_outbound_calls_counter().add(1, {API_ATTRIBUTE_NAMES.operation: operation})


def record_outbound_error(operation: str) -> None:
    get_outbound_errors_counter().add(1, {API_ATTRIBUTE_NAMES.operation: operation})


def record_exception(span: Span, exception: BaseException) -> None:
    span.record_exception(exception)
    span.set_status(Status(StatusCode.ERROR, str(exception)))
