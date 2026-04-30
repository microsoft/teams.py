"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import logging
import re
from typing import Optional

from microsoft_teams.api.auth.cloud_environment import CloudEnvironment
from microsoft_teams.common.http.client_token import Token

logger = logging.getLogger(__name__)

# Extracts scheme + host (+ optional port) from a URL-like scope such as
# "https://graph.microsoft.us/.default" -> "https://graph.microsoft.us".
_GRAPH_BASE_URL_RE = re.compile(r"^(https?://[^/]+)", re.IGNORECASE)


def _derive_graph_base_url(cloud: Optional[CloudEnvironment]) -> Optional[str]:
    """Derive the Graph API base URL from a cloud's graph_scope, or None if unavailable."""
    if cloud is None:
        return None
    scope = cloud.graph_scope.strip()
    if not scope:
        return None
    match = _GRAPH_BASE_URL_RE.match(scope)
    if match is None:
        logger.warning(
            "graph_scope %r is not a URL; Graph calls will route to the public cloud. "
            "Set graph_scope to an 'https://<host>/.default' value to route to the correct Graph endpoint.",
            scope,
        )
        return None
    return match.group(1)


def create_graph_client(token: Token, cloud: Optional[CloudEnvironment] = None):
    """Lazy import and create a Graph client with the given token.

    Args:
        token: The token used to authenticate Graph requests.
        cloud: Optional cloud environment. When provided (and non-None), the Graph client
            routes HTTP calls to the cloud's Graph endpoint derived from ``graph_scope``.
            When ``None``, the public Graph endpoint is used.
    """
    try:
        from microsoft_teams.graph import get_graph_client

        return get_graph_client(token, base_url=_derive_graph_base_url(cloud))
    except ImportError as exc:
        raise ImportError(
            "Graph functionality not available. Install with 'pip install microsoft-teams-apps[graph]'"
        ) from exc
