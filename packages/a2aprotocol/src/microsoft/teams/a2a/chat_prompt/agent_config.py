"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from pydantic import BaseModel

from .types import BuildFunctionMetadata, BuildMessageForAgent, BuildMessageFromAgentResponse


class AgentConfig(BaseModel):
    key: str
    base_url: str
    card_url: str
    build_function_metadata: Optional[BuildFunctionMetadata] = None
    build_message_for_agent: Optional[BuildMessageForAgent] = None
    build_message_from_agent_response: Optional[BuildMessageFromAgentResponse] = None
