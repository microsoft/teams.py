"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from dataclasses import dataclass, field
from logging import Logger
from typing import Any, Callable, List, Optional, TypedDict, Union

from a2a.client import Client
from a2a.types import AgentCard, Message, Task


@dataclass
class FunctionMetadata:
    name: str
    description: str


@dataclass
class AgentPromptParams:
    card: AgentCard
    client: Client


@dataclass
class BuildPromptMetadata:
    system_prompt: Optional[str] = None
    agent_details: List[AgentPromptParams] = field(default_factory=lambda: [])


@dataclass
class BuildMessageForAgentMetadata:
    card: AgentCard
    input: str
    metadata: Optional[dict[str, Any]] = None


@dataclass
class BuildMessageFromAgentMetadata:
    card: AgentCard
    response: Union[Task, Message]
    original_input: str


BuildFunctionMetadata = Callable[[AgentCard], FunctionMetadata]
BuildPrompt = Callable[[BuildPromptMetadata], Optional[str]]
BuildMessageForAgent = Callable[[BuildMessageForAgentMetadata], Union[Message, str]]
BuildMessageFromAgentResponse = Callable[[BuildMessageFromAgentMetadata], str]


class A2AClientPluginOptions(TypedDict, total=False):
    """
    Options for constructing an A2AClientPlugin using the official SDK.
    """

    build_function_metadata: Optional[BuildFunctionMetadata]
    "Optional function to customize the function name and description for each agent card."
    build_prompt: Optional[BuildPrompt]
    "Optional function to customize the prompt given all agent cards."
    build_message_for_agent: Optional[BuildMessageForAgent]
    "Optional function to customize the message format sent to each agent."
    build_message_from_agent_response: Optional[BuildMessageFromAgentResponse]
    "Optional function to customize how agent responses are processed into strings."
    logger: Optional[Logger]
    "The associated logger"


@dataclass
class InternalA2AClientPluginOptions:
    """Internal dataclass for A2AClientPluginOptions with defaults and non-nullable fields."""

    # Optional fields
    build_function_metadata: Optional[BuildFunctionMetadata] = None
    build_prompt: Optional[BuildPrompt] = None
    build_message_for_agent: Optional[BuildMessageForAgent] = None
    build_message_from_agent_response: Optional[BuildMessageFromAgentResponse] = None
    logger: Optional[Logger] = None

    @classmethod
    def from_typed_dict(cls, options: A2AClientPluginOptions) -> "InternalA2AClientPluginOptions":
        """
        Create InternalA2AClientPluginOptions from A2AClientPluginOptions TypedDict.

        Args:
            options: A2AClientPluginOptions TypedDict

        Returns:
            InternalA2AClientPluginOptions with proper defaults and non-nullable required fields
        """
        kwargs: dict[str, Any] = {k: v for k, v in options.items() if v is not None}
        return cls(**kwargs)


@dataclass
class A2APluginUseParams:
    """
    Parameters for registering an agent with the A2AClientPlugin.
    """

    key: str
    "Unique key to identify this agent"
    base_url: str
    "Base URL to the agent's card"
    card_url: str
    "URL to the agent's card endpoint"
    build_function_metadata: Optional[BuildFunctionMetadata] = None
    "Custom function metadata builder for this specific agent"
    build_message_for_agent: Optional[BuildMessageForAgent] = None
    "Custom message builder for this specific agent"
    build_message_from_agent_response: Optional[BuildMessageFromAgentResponse] = None
    "Custom response processor for this specific agent"
