"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from dataclasses import field
from typing import Any, Callable, List, Optional, Union

from a2a.client import A2AClient
from a2a.types import AgentCard, Message, Task
from microsoft.teams.common import ConsoleLogger
from pydantic import BaseModel


class FunctionMetadata(BaseModel):
    name: str
    description: str


class AgentPromptParams(BaseModel):
    card: AgentCard
    client: A2AClient


class BuildPromptMetadata(BaseModel):
    system_prompt: Optional[str] = None
    agent_details: List[AgentPromptParams] = field(default_factory=lambda: [])


class BuildMessageForAgentMetadata(BaseModel):
    card: AgentCard
    input: str
    metadata: Optional[dict[str, Any]] = None


class BuildMessageFromAgentMetadata(BaseModel):
    card: AgentCard
    response: Union[Task, Message]
    original_input: str


BuildFunctionMetadata = Callable[[AgentCard], FunctionMetadata]
BuildPrompt = Callable[[BuildPromptMetadata], Optional[str]]
BuildMessageForAgent = Callable[[BuildMessageForAgentMetadata], Union[Message, str]]
BuildMessageFromAgentResponse = Callable[[BuildMessageFromAgentMetadata], str]


class A2AClientPluginOptions(BaseModel):
    """
    Options for constructing an A2AClientPlugin using the official SDK.
    """

    build_function_metadata: Optional[BuildFunctionMetadata] = None
    "Optional function to customize the function name and description for each agent card."
    build_prompt: Optional[BuildPrompt] = None
    "Optional function to customize the prompt given all agent cards."
    build_message_for_agent: Optional[BuildMessageForAgent] = None
    "Optional function to customize the message format sent to each agent."
    build_message_from_agent_response: Optional[BuildMessageFromAgentResponse] = None
    "Optional function to customize how agent responses are processed into strings."
    logger: Optional[ConsoleLogger] = None
    "The associated logger"


class A2APluginUseParams(BaseModel):
    """
    Parameters for registering an agent with the A2AClientPlugin.
    """

    key: str
    "Unique key to identify this agent"
    card_url: str
    "URL to the agent's card endpoint"
    build_function_metadata: Optional[BuildFunctionMetadata] = None
    "Custom function metadata builder for this specific agent"
    build_message_for_agent: Optional[BuildMessageForAgent] = None
    "Custom message builder for this specific agent"
    build_message_from_agent_response: Optional[BuildMessageFromAgentResponse] = None
    "Custom response processor for this specific agent"
