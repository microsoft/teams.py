"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from contextlib import contextmanager
from dataclasses import dataclass
from time import perf_counter
from typing import Generator, Optional

from httpx import HTTPStatusError
from opentelemetry import metrics, trace
from opentelemetry.metrics import Counter, Histogram, Meter
from opentelemetry.trace import Span, Status, StatusCode, Tracer

from ._constants import (
    APP_ATTRIBUTE_NAMES,
    APP_METRIC_NAMES,
    APP_OAUTH_ERROR_TYPES,
    APP_OAUTH_RESULTS,
    APP_SPAN_NAMES,
)
from ._telemetry import TeamsBotApplicationTelemetry


@dataclass
class OAuthOperationTelemetry:
    result: str = APP_OAUTH_RESULTS.failure


def get_tracer() -> Tracer:
    return trace.get_tracer(
        TeamsBotApplicationTelemetry.tracer_name,
        instrumenting_library_version=TeamsBotApplicationTelemetry.instrumentation_version,
    )


def get_meter() -> Meter:
    return metrics.get_meter(
        TeamsBotApplicationTelemetry.meter_name,
        version=TeamsBotApplicationTelemetry.instrumentation_version,
    )


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


def get_oauth_errors_counter() -> Counter:
    return get_meter().create_counter(APP_METRIC_NAMES.oauth_errors)


def get_oauth_operation_duration_histogram() -> Histogram:
    return get_meter().create_histogram(APP_METRIC_NAMES.oauth_operation_duration, unit="ms")


def get_oauth_operations_counter() -> Counter:
    return get_meter().create_counter(APP_METRIC_NAMES.oauth_operations)


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


def record_oauth_error(connection_name: str, operation: str, error_type: str) -> None:
    get_oauth_errors_counter().add(
        1,
        {
            APP_ATTRIBUTE_NAMES.oauth_connection: connection_name,
            APP_ATTRIBUTE_NAMES.oauth_operation: operation,
            APP_ATTRIBUTE_NAMES.oauth_error_type: error_type,
        },
    )


def record_oauth_operation(connection_name: Optional[str], operation: str, result: str, duration_ms: float) -> None:
    """Record an OAuth operation.

    ``connection_name`` is optional because a ``signin/failure`` callback cannot
    always be attributed to a connection. When it is ``None`` the connection
    attribute is omitted rather than guessed, so queries never see an unrelated
    connection blamed for the failure.
    """
    attributes = {
        APP_ATTRIBUTE_NAMES.oauth_operation: operation,
        APP_ATTRIBUTE_NAMES.oauth_result: result,
    }
    if connection_name is not None:
        attributes[APP_ATTRIBUTE_NAMES.oauth_connection] = connection_name
    get_oauth_operations_counter().add(1, attributes)
    get_oauth_operation_duration_histogram().record(duration_ms, attributes)


def record_turn_duration(duration_ms: float, activity_type: str) -> None:
    get_turn_duration_histogram().record(duration_ms, {APP_ATTRIBUTE_NAMES.activity_type: activity_type})


def record_exception(span: Span, exception: BaseException) -> None:
    span.record_exception(exception)
    span.set_status(Status(StatusCode.ERROR, str(exception)))


@contextmanager
def trace_oauth_operation(
    connection_name: str,
    operation: str,
) -> Generator[tuple[Span, OAuthOperationTelemetry], None, None]:
    """Trace and measure one OAuth flow operation."""
    started_at = perf_counter()
    telemetry = OAuthOperationTelemetry()
    with get_tracer().start_as_current_span(
        APP_SPAN_NAMES.oauth,
        record_exception=False,
        set_status_on_exception=False,
    ) as span:
        span.set_attribute(APP_ATTRIBUTE_NAMES.oauth_connection, connection_name)
        span.set_attribute(APP_ATTRIBUTE_NAMES.oauth_operation, operation)
        try:
            yield span, telemetry
        except Exception as exception:
            error_type = (
                APP_OAUTH_ERROR_TYPES.http_error
                if isinstance(exception, HTTPStatusError)
                else APP_OAUTH_ERROR_TYPES.exception
            )
            span.set_attribute(APP_ATTRIBUTE_NAMES.oauth_error_type, error_type)
            record_exception(span, exception)
            record_oauth_error(connection_name, operation, error_type)
            raise
        finally:
            span.set_attribute(APP_ATTRIBUTE_NAMES.oauth_result, telemetry.result)
            record_oauth_operation(
                connection_name,
                operation,
                telemetry.result,
                (perf_counter() - started_at) * 1000,
            )
