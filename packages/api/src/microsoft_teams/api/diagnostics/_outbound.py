"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import inspect
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field

import httpx
from microsoft_teams.common import Client
from microsoft_teams.common.http import MiddlewareContext, MiddlewareNext
from opentelemetry.trace import Span, SpanKind

from ._constants import API_SPAN_NAMES
from ._helpers import get_tracer, record_exception, record_outbound_call, record_outbound_error

ApiOutboundResponseHook = Callable[[Span, httpx.Response], None | Awaitable[None]]


@dataclass(frozen=True)
class ApiOutboundTelemetryMetadata:
    operation: str
    attributes: Mapping[str, str] = field(default_factory=dict[str, str])
    on_response: ApiOutboundResponseHook | None = None


class ApiOutboundTelemetryMiddleware:
    async def send(
        self,
        context: MiddlewareContext,
        next: MiddlewareNext,
    ) -> httpx.Response:
        metadata = context.metadata
        if not isinstance(metadata, ApiOutboundTelemetryMetadata):
            return await next()

        record_outbound_call(metadata.operation)
        with get_tracer().start_as_current_span(
            API_SPAN_NAMES.api_client,
            attributes=dict(metadata.attributes),
            kind=SpanKind.CLIENT,
            record_exception=False,
            set_status_on_exception=False,
        ) as span:
            try:
                response = await next()
            except Exception as exception:
                record_exception(span, exception)
                record_outbound_error(metadata.operation)
                raise

            if metadata.on_response is not None:
                hook_result = metadata.on_response(span, response)
                if inspect.isawaitable(hook_result):
                    await hook_result
            return response


def ensure_outbound_telemetry_middleware(client: Client) -> None:
    if not any(isinstance(middleware, ApiOutboundTelemetryMiddleware) for middleware in client.middlewares):
        client.use(ApiOutboundTelemetryMiddleware())
