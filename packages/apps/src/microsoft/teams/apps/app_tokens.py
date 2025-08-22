"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from dataclasses import dataclass
from typing import Optional

from microsoft.teams.api.auth.token import TokenProtocol


@dataclass
class AppTokens:
    """Application tokens for API access."""

    bot: Optional[TokenProtocol] = None
    graph: Optional[TokenProtocol] = None
