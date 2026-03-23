"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from microsoft_teams.api import Activity, InvokeResponse, TokenProtocol


@dataclass
class RouteContext:
    port: int
    process: Callable[[TokenProtocol, Activity], Awaitable[InvokeResponse[Any]]]
