"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from .agent_client_info import AgentClientInfo
from .agent_config import AgentConfig
from .plugin import A2AClientPlugin, A2AClientPluginOptions, A2APluginUseParams, FunctionMetadata
from .types import (
    BuildFunctionMetadata,
    BuildMessageForAgent,
    BuildMessageForAgentMetadata,
    BuildMessageFromAgentMetadata,
    BuildMessageFromAgentResponse,
)

__all__ = [
    "AgentClientInfo",
    "AgentConfig",
    "A2AClientPlugin",
    "BuildFunctionMetadata",
    "BuildMessageForAgent",
    "BuildMessageFromAgentResponse",
    "A2AClientPluginOptions",
    "A2APluginUseParams",
    "BuildMessageForAgentMetadata",
    "BuildMessageFromAgentMetadata",
    "FunctionMetadata",
]
