"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from __future__ import annotations

import inspect
import logging
from typing import Any, Awaitable, Callable, Optional, Union

from microsoft_agents.hosting.core.channel_adapter import ChannelAdapter

from .context import agent_sdk_context

logger = logging.getLogger(__name__)

# Routing key used to select the connection that mints agentic tokens,
# mirroring the Agents SDK's ``get_token_provider(identity, "agentic")``
# convention (and the ``CONNECTIONSMAP ... SERVICEURL=agentic`` entry). When no
# dedicated agentic connection is registered the lookup falls back to the
# default connection, which is sufficient for the single-connection case.
_AGENTIC_ROUTING_KEY = "agentic"


def make_agent_sdk_token_provider(
    connection_manager: Any,
) -> Callable[..., Awaitable[str]]:
    async def _token(
        scope: Union[str, list[str]],
        tenant_id: Optional[str] = None,
        *,
        agentic_identity: Optional[Any] = None,
    ) -> str:
        scopes = [scope] if isinstance(scope, str) else list(scope)

        agentic_user_id = getattr(agentic_identity, "agentic_user_id", None)
        if agentic_identity is not None and agentic_user_id:
            provider = _select_provider(connection_manager, _AGENTIC_ROUTING_KEY)
            token = await provider.get_agentic_user_token(
                getattr(agentic_identity, "tenant_id", None) or tenant_id,
                agentic_identity.agentic_app_id,
                agentic_user_id,
                scopes,
            )
            if not token:
                raise RuntimeError(
                    "Agents SDK connection returned no agentic user token; the "
                    "connection must be an MSAL provider with agentic support."
                )
            return token

        # Non-agentic path: outbound Bot Framework Service token. Strip
        # ".default" off the first scope to derive the resource_url MSAL wants
        # — '.default' is appended back internally.
        first = scopes[0] if scopes else ""
        resource_url = first[: -len("/.default")] if first.endswith("/.default") else first

        provider = _select_provider(connection_manager, resource_url)
        result = provider.get_access_token(resource_url, scopes)
        if inspect.isawaitable(result):
            result = await result
        return result

    return _token


def _select_provider(connection_manager: Any, service_url: str) -> Any:
    context = agent_sdk_context.get(None)
    if context is None:
        return connection_manager.get_default_connection()

    claims_identity = context.turn_state.get(ChannelAdapter.AGENT_IDENTITY_KEY)
    if claims_identity is None:
        return connection_manager.get_default_connection()

    target_url = service_url or (context.activity.service_url or "")
    if not target_url:
        return connection_manager.get_default_connection()

    try:
        return connection_manager.get_token_provider(claims_identity, target_url)
    except Exception as exc:  # noqa: BLE001 — degrade gracefully on lookup failure
        logger.debug(
            "connection lookup failed (%s); using default connection",
            exc,
        )
        return connection_manager.get_default_connection()
