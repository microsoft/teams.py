"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from dataclasses import dataclass
from logging import Logger
from typing import Any, Awaitable, Callable

from microsoft.teams.api import Activity, InvokeResponse, TokenProtocol


@dataclass
class RouteContext:
    port: int
    log: Logger
    process: Callable[[TokenProtocol, Activity], Awaitable[InvokeResponse[Any]]]
