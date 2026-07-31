"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import os
from dataclasses import dataclass, field

from microsoft.opentelemetry import use_microsoft_opentelemetry
from microsoft_teams.apps import AppTokenProvider
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

# OAuth scope for the first-party Agent365 observability service. Override it
# with A365_OBSERVABILITY_SCOPE_OVERRIDE for a different observability resource.
OBSERVABILITY_SCOPE = os.getenv(
    "A365_OBSERVABILITY_SCOPE_OVERRIDE",
    "api://9b975845-388f-4429-889e-eab1ef63949c/.default",
)


@dataclass
class Agent365TokenCache:
    """Async refresh plus synchronous lookup for the Python Agent365 exporter."""

    _tokens: dict[tuple[str, str], str] = field(default_factory=lambda: dict[tuple[str, str], str]())

    async def refresh(
        self,
        token_provider: AppTokenProvider,
        agentic_app_instance_id: str,
        tenant_id: str,
    ) -> None:
        token = await token_provider.get_agentic_app_instance_token(
            OBSERVABILITY_SCOPE,
            agentic_app_instance_id,
            tenant_id,
        )
        value = str(token) if token is not None else None
        if not value:
            raise RuntimeError(
                "Agent365 exporter could not mint an app token. Check CLIENT_ID, CLIENT_SECRET, and TENANT_ID."
            )
        self._tokens[(agentic_app_instance_id, tenant_id)] = value

    def resolve(self, agentic_app_instance_id: str, tenant_id: str) -> str | None:
        return self._tokens.get((agentic_app_instance_id, tenant_id))


def use_agent365_exporter(token_cache: Agent365TokenCache) -> None:
    """Configure the app-level Microsoft OpenTelemetry Agent365 exporter."""
    use_microsoft_opentelemetry(
        enable_a365=True,
        a365_enable_observability_exporter=True,
        a365_use_s2s_endpoint=True,
        a365_observability_scope_override=OBSERVABILITY_SCOPE,
        a365_token_resolver=token_cache.resolve,
        enable_sensitive_data=False,
        instrumentation_options={"openai_agents": {"enabled": False}},
    )


def flush_agent365_spans() -> None:
    """Flush queued spans before a short-lived process exits."""
    provider = trace.get_tracer_provider()
    if not isinstance(provider, TracerProvider):
        raise RuntimeError("Microsoft OpenTelemetry did not configure an SDK tracer provider")
    provider.force_flush()
