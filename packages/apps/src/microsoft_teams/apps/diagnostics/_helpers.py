"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from opentelemetry import metrics, trace
from opentelemetry.metrics import Counter, Histogram, Meter
from opentelemetry.trace import Span, Status, StatusCode, Tracer

from ._constants import APP_ATTRIBUTE_NAMES, APP_METRIC_NAMES
from ._telemetry import TeamsBotApplicationTelemetry


def get_tracer() -> Tracer:
    return trace.get_tracer(TeamsBotApplicationTelemetry.tracer_name)


def get_meter() -> Meter:
    return metrics.get_meter(TeamsBotApplicationTelemetry.meter_name)


def get_activities_received_counter() -> Counter:
    return get_meter().create_counter(APP_METRIC_NAMES.activities_received)


def get_handler_dispatched_counter() -> Counter:
    return get_meter().create_counter(APP_METRIC_NAMES.handler_dispatched)


def get_handler_duration_histogram() -> Histogram:
    return get_meter().create_histogram(APP_METRIC_NAMES.handler_duration, unit="ms")


def get_handler_failures_counter() -> Counter:
    return get_meter().create_counter(APP_METRIC_NAMES.handler_failures)


def get_handler_unmatched_counter() -> Counter:
    return get_meter().create_counter(APP_METRIC_NAMES.handler_unmatched)


def get_turn_duration_histogram() -> Histogram:
    return get_meter().create_histogram(APP_METRIC_NAMES.turn_duration, unit="ms")


def record_activity_received(activity_type: str) -> None:
    get_activities_received_counter().add(1, {APP_ATTRIBUTE_NAMES.activity_type: activity_type})


def record_handler_dispatched(handler_type: str, handler_dispatch: str) -> None:
    get_handler_dispatched_counter().add(
        1,
        {
            APP_ATTRIBUTE_NAMES.handler_type: handler_type,
            APP_ATTRIBUTE_NAMES.handler_dispatch: handler_dispatch,
        },
    )


def record_handler_duration(duration_ms: float, handler_type: str, handler_dispatch: str) -> None:
    get_handler_duration_histogram().record(
        duration_ms,
        {
            APP_ATTRIBUTE_NAMES.handler_type: handler_type,
            APP_ATTRIBUTE_NAMES.handler_dispatch: handler_dispatch,
        },
    )


def record_handler_failure(handler_type: str, handler_dispatch: str) -> None:
    get_handler_failures_counter().add(
        1,
        {
            APP_ATTRIBUTE_NAMES.handler_type: handler_type,
            APP_ATTRIBUTE_NAMES.handler_dispatch: handler_dispatch,
        },
    )


def record_handler_unmatched(activity_type: str, invoke_name: str | None = None) -> None:
    attributes = {APP_ATTRIBUTE_NAMES.activity_type: activity_type}
    if invoke_name:
        attributes[APP_ATTRIBUTE_NAMES.invoke_name] = invoke_name
    get_handler_unmatched_counter().add(1, attributes)


def record_turn_duration(duration_ms: float, activity_type: str) -> None:
    get_turn_duration_histogram().record(duration_ms, {APP_ATTRIBUTE_NAMES.activity_type: activity_type})


def record_exception(span: Span, exception: BaseException) -> None:
    span.record_exception(exception)
    span.set_status(Status(StatusCode.ERROR, str(exception)))
