"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from dataclasses import dataclass
from typing import Optional

from .types import BuildFunctionMetadata, BuildMessageForAgent, BuildMessageFromAgentResponse


@dataclass
class AgentConfig:
    key: str
    base_url: str
    card_url: str
    build_function_metadata: Optional[BuildFunctionMetadata] = None
    "Optional function to customize the function name and description for each agent card."
    build_message_for_agent: Optional[BuildMessageForAgent] = None
    "Optional function to customize the message format sent to each agent."
    build_message_from_agent_response: Optional[BuildMessageFromAgentResponse] = None
    "Optional function to customize how agent responses are processed into strings."
