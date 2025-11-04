"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from dataclasses import dataclass
from typing import Optional

from a2a.server.agent_execution import AgentExecutor
from a2a.server.tasks import TaskStore
from a2a.types import AgentCard
from a2a.utils.constants import AGENT_CARD_WELL_KNOWN_PATH


@dataclass
class A2APluginOptions:
    agent_card: AgentCard
    "The agent card to be used for the A2A plugin."
    path: Optional[str] = "/a2a"
    "Path to the A2A server, by default is `a2a`."
    agent_card_path: Optional[str] = AGENT_CARD_WELL_KNOWN_PATH
    "Path to the agent card, by default is `/.well-known/agent-card.json`."
    task_store: Optional[TaskStore] = None
    """
    TaskStore which stores the tasks that are sent to the agent or that the agent sends.
    If not provided, the App's storage will be used.
    """
    agent_executor: Optional[AgentExecutor] = None
    """
     For a completely custom executor, you may provide your own executor that will
     get executed whenever the a2a agent is InMemoryTaskStore
    """
