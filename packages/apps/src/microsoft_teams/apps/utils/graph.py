"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from microsoft_teams.common.http.client_token import Token


def create_graph_client(token: Token):
    """Lazy import and create a Graph client with the given token."""
    try:
        from microsoft_teams.graph import get_graph_client

        return get_graph_client(token)
    except ImportError as exc:
        raise ImportError(
            "Graph functionality not available. Install with 'pip install microsoft-teams-apps[graph]'"
        ) from exc
