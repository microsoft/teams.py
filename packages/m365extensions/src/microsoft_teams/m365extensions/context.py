"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from __future__ import annotations

from contextvars import ContextVar

from microsoft_agents.hosting.core.turn_context import TurnContext

# Internal only: the middleware sets this for the duration of a teams.py-handled
# turn so ``credentials._select_provider`` can pick the connection that matches
# the inbound identity. It is deliberately not exposed as a public accessor.
agent_sdk_context: ContextVar[TurnContext] = ContextVar("teams_sdk.agent_sdk_context")
