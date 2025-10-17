"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from pydantic import ConfigDict

from a2a.client import Client
from a2a.types import AgentCard

from .agent_config import AgentConfig


class AgentClientInfo(AgentConfig):
    client: Client
    agent_card: AgentCard

    model_config = ConfigDict(arbitrary_types_allowed=True)
