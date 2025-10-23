"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from dataclasses import dataclass

from a2a.client import Client
from a2a.types import AgentCard

from .agent_config import AgentConfig


@dataclass(kw_only=True)
class AgentClientInfo(AgentConfig):
    client: Client
    agent_card: AgentCard
