"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import re
import uuid
from dataclasses import asdict
from functools import partial
from logging import Logger
from typing import Any, Dict, List, Optional, Union, Unpack, cast

from httpx import AsyncClient
from microsoft.teams.ai import Function as ChatFunction
from microsoft.teams.ai import SystemMessage
from microsoft.teams.ai.plugin import BaseAIPlugin
from microsoft.teams.common.logging.console import ConsoleLogger
from pydantic import BaseModel

from a2a.client import ClientFactory
from a2a.client.card_resolver import A2ACardResolver
from a2a.client.client import ClientConfig
from a2a.types import AgentCard, Message, Part, Role, Task, TextPart

from .agent_client_info import AgentClientInfo
from .agent_config import AgentConfig
from .types import (
    A2AClientPluginOptions,
    A2APluginUseParams,
    AgentPromptParams,
    BuildFunctionMetadata,
    BuildMessageForAgent,
    BuildMessageForAgentMetadata,
    BuildMessageFromAgentMetadata,
    BuildMessageFromAgentResponse,
    BuildPrompt,
    BuildPromptMetadata,
    FunctionMetadata,
    InternalA2AClientPluginOptions,
)


class A2AClientMessageParams(BaseModel):
    message: str
    "The message to send to the agent"


class A2AClientPlugin(BaseAIPlugin):
    log: Logger
    _agent_configs: Dict[str, AgentConfig] = {}
    _clients: Dict[str, AgentClientInfo] = {}

    _build_function_metadata: Optional[BuildFunctionMetadata] = None
    _build_prompt: Optional[BuildPrompt] = None
    _build_message_for_agent: Optional[BuildMessageForAgent] = None
    _build_message_from_agent_response: Optional[BuildMessageFromAgentResponse] = None

    def __init__(self, **options: Unpack[A2AClientPluginOptions]):
        super().__init__("a2a")

        self.options = InternalA2AClientPluginOptions.from_typed_dict(options)
        self._build_function_metadata = self.options.build_function_metadata
        self._build_prompt = self.options.build_prompt
        self._build_message_for_agent = self.options.build_message_for_agent
        self._build_message_from_agent_response = self.options.build_message_from_agent_response
        self.log = self.options.logger if self.options.logger else ConsoleLogger().create_logger(name="a2a:client")

    def on_use_plugin(self, args: A2APluginUseParams):
        # just store the config, defer client creation to on_build_functions
        self._agent_configs.update(
            {
                args.key: AgentConfig(
                    key=args.key,
                    base_url=args.base_url,
                    card_url=args.card_url,
                    build_function_metadata=args.build_function_metadata,
                    build_message_for_agent=args.build_message_for_agent,
                    build_message_from_agent_response=args.build_message_from_agent_response,
                )
            }
        )

    async def fetch_agent_card(self, base_url: str, card_url: str) -> AgentCard:
        async with AsyncClient() as httpx_client:
            resolver = A2ACardResolver(httpx_client, base_url)
            card = await resolver.get_agent_card(card_url)
            return card

    async def _get_agent_card(self, key: str, config: AgentConfig) -> Optional[AgentCard]:
        # return cached client info if it exists
        client_info = self._clients.get(key)

        if client_info:
            return client_info.agent_card

        # create new client and get agent card
        try:
            card = await self.fetch_agent_card(base_url=config.base_url, card_url=config.card_url)
            client_config = ClientConfig()
            client = ClientFactory(client_config).create(card=card)
            client_info = AgentClientInfo(**asdict(config), client=client, agent_card=card)
            self._clients.update({key: client_info})
            return card
        except Exception as e:
            self.log.error(f"Error creating client or fetching agent card for {key}: {e}")
            return None

    def _default_function_metadata(self, card: AgentCard) -> FunctionMetadata:
        name = f"message_{re.sub(r'(?<!^)(?=[A-Z])', '_', card.name).lower()}"
        description = card.description or f"Interact with {card.name} agent"
        return FunctionMetadata(name=name, description=description)

    def _create_message(
        self, text: str, card: Optional[AgentCard] = None, metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        return Message(
            message_id=str(uuid.uuid4()),
            role=Role("user"),
            parts=[Part(root=TextPart(kind="text", text=text))],
            metadata=metadata,
        )

    def _default_build_message(self, card: AgentCard, input: str, metadata: Optional[Dict[str, Any]] = None) -> Message:
        return self._create_message(input, card, metadata)

    def _default_build_message_from_agent_response(
        self, card: AgentCard, response: Union[Message, Task], original_input: str
    ) -> str:
        if isinstance(response, Message):
            text_parts: List[str] = []
            for part in response.parts:
                if getattr(part.root, "kind", None) == "text":
                    text_part = cast(TextPart, part.root)
                    text_parts.append(text_part.text)
            return " ".join(text_parts) or "Agent responded with no text content."
        else:
            return "Agent responded with non-message content."

    async def on_build_functions(self, functions: list[ChatFunction[Any]]) -> list[ChatFunction[Any]] | None:
        all_functions: List[ChatFunction[Any]] = []

        for key, config in self._agent_configs.items():
            try:
                agent_card = await self._get_agent_card(key, config)
                if not agent_card:
                    self.log.warning(f"Could not retrieve agent card for {key}, continuing to next agent.")
                    # skip if we couldn't get the agent card
                    continue

                # use custom function metadata builder or default
                build_metadata = (
                    config.build_function_metadata or self._build_function_metadata or self._default_function_metadata
                )

                metadata = build_metadata(agent_card)
                name = metadata.name
                description = metadata.description

                async def message_handler(
                    params: A2AClientMessageParams, config: AgentConfig, agent_card: AgentCard, key: str
                ) -> Any:
                    try:
                        agent_message = params.message

                        # use custom message builder if provided, otherwise use default
                        metadata = BuildMessageForAgentMetadata(card=agent_card, input=agent_message)
                        msg_or_str = (
                            config.build_message_for_agent(metadata)
                            if config.build_message_for_agent
                            else self._build_message_for_agent(metadata)
                            if self._build_message_for_agent
                            else self._default_build_message(agent_card, agent_message)
                        )

                        # handle both message and string returns
                        if isinstance(msg_or_str, str):
                            message = self._create_message(msg_or_str, agent_card)
                        else:
                            message = msg_or_str

                        # get the client info to send the message
                        client_info = self._clients.get(key)
                        if not client_info:
                            raise ValueError(f"Client not found for agent {key}")

                        self.log.debug(f"Calling agent {agent_card.name} with {message.model_dump_json()}")

                        last_message: Optional[Message] = None
                        async for event in client_info.client.send_message(message):
                            # Unwrap tuple from transport implementations
                            if isinstance(event, tuple):
                                event = event[0]
                            if isinstance(event, Message):
                                last_message = event

                        if last_message is not None:
                            self.log.debug(f"Got response from {agent_card.name}")
                            # use custom response builder if provided, otherwise use default
                            metadata = BuildMessageFromAgentMetadata(
                                card=agent_card, response=last_message, original_input=agent_message
                            )
                            return (
                                config.build_message_from_agent_response(metadata)
                                if config.build_message_from_agent_response
                                else self._build_message_from_agent_response(metadata)
                                if self._build_message_from_agent_response
                                else self._default_build_message_from_agent_response(
                                    agent_card, last_message, agent_message
                                )
                            )
                    except Exception as e:
                        self.log.error(e)
                        raise e

                message_handler_with_args = partial(message_handler, config=config, agent_card=agent_card, key=key)

                all_functions.append(
                    ChatFunction(
                        name=name,
                        description=description,
                        parameter_schema=A2AClientMessageParams,
                        handler=message_handler_with_args,
                    )
                )
                self.log.debug(f"Added function in ChatPrompt to call {agent_card.name}")
            except Exception as e:
                self.log.info(f"Failed to build function for agent {key}: {e}")
                # Continue with other agents even if one fails

        functions = functions + all_functions
        return functions

    async def on_build_instructions(self, instructions: Optional[SystemMessage] = None) -> Optional[SystemMessage]:
        # collect agent details for prompt building
        agent_prompt_params: List[AgentPromptParams] = []

        for key, config in self._agent_configs.items():
            try:
                agent_card = await self._get_agent_card(key, config)
                if agent_card:
                    client_info = self._clients.get(key)
                    if client_info:
                        agent_prompt_params.append(
                            AgentPromptParams(
                                card=agent_card,
                                client=client_info.client,
                            )
                        )
            except Exception as e:
                self.log.info(f"Failed to get agent card for {key}: {e}")

        # use custom build_prompt if provided, otherwise use default
        if self._build_prompt:
            metadata = BuildPromptMetadata(
                system_prompt=instructions.content if instructions else None, agent_details=agent_prompt_params
            )
            content = self._build_prompt(metadata)
            return SystemMessage(content=content or "")

        # default prompt building
        if len(agent_prompt_params) == 0:
            return instructions

        agent_details = "".join(
            [
                f"<Agent Details>\n<Name>\n{param.card.name}\n</Name>\n"
                + (f"<Description>\n{param.card.description}\n</Description>\n" if param.card.description else "")
                + "".join(
                    [
                        f'<SKILL name="{skill.name}" description="{skill.description}" />\n'
                        + (f"<EXAMPLES>\n{'\n'.join(skill.examples)}\n</EXAMPLES>\n" if skill.examples else "")
                        for skill in param.card.skills
                    ]
                )
                # could add client specific info here if needed
                + "</Agent Details>\n"
                for param in agent_prompt_params
            ]
        )

        prompt = (
            (instructions.content if instructions else "")
            + "\n\nHere are details about available agents that you can message:\n"
            + agent_details
        )

        return SystemMessage(content=prompt)
