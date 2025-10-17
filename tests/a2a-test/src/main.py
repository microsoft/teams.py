"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import re
import uuid
from os import getenv
from typing import List, Union, cast

from a2a.types import AgentCapabilities, AgentCard, AgentSkill, Message, Part, Role, TextPart
from microsoft.teams.a2a import (
    A2AClientPlugin,
    A2AClientPluginOptions,
    A2AMessageEvent,
    A2AMessageEventKey,
    A2APlugin,
    A2APluginOptions,
    A2APluginUseParams,
    BuildMessageForAgentMetadata,
    BuildMessageFromAgentMetadata,
    FunctionMetadata,
)
from microsoft.teams.ai import ChatPrompt, Function, ModelMessage
from microsoft.teams.api import MessageActivity, TypingActivityInput
from microsoft.teams.apps import ActivityContext, App, PluginBase
from microsoft.teams.common import ConsoleLogger, ConsoleLoggerOptions
from microsoft.teams.devtools import DevToolsPlugin
from microsoft.teams.openai.completions_model import OpenAICompletionsAIModel
from pydantic import BaseModel

logger = ConsoleLogger().create_logger("a2a", ConsoleLoggerOptions(level="debug"))
PORT = getenv("PORT", "4000")


# Setup AI
def get_required_env(key: str) -> str:
    value = getenv(key)
    if not value:
        raise ValueError(f"Required environment variable {key} is not set")
    return value


AZURE_OPENAI_MODEL = get_required_env("AZURE_OPENAI_MODEL")
completions_model = OpenAICompletionsAIModel(model=AZURE_OPENAI_MODEL)

# Setup A2A Client Plugin
client_plugin = A2AClientPlugin(A2AClientPluginOptions())
# Specify the connection details for the agent we want to use
client_plugin.on_use_plugin(
    A2APluginUseParams(
        key="my-weather-agent", base_url=f"http://localhost:{PORT}/a2a", card_url=".well-known/agent-card.json"
    )
)
prompt = ChatPrompt(
    model=completions_model,
    plugins=[client_plugin],
)


def build_function_metadata(card: AgentCard) -> FunctionMetadata:
    return FunctionMetadata(
        name=f"ask{re.sub(r'\s+', '', card.name)}",
        description=f"Ask {card.name} about {card.description or 'anything'}",
    )


def build_message_for_agent(data: BuildMessageForAgentMetadata) -> Union[Message, str]:
    # Return a string - will be automatically wrapped in a Message
    return f"[To {data.card.name}]: {data.input}"

    # Uncomment the following block to return a full Message object
    # message = Message(


#                 kind='message',
#                 message_id=str(uuid4()),
#                 role=Role('user'),
#                 parts=[Part(root=TextPart(kind='text', text=f"[To {data.card.name}]: {data.input}"))],
#                 metadata={"source": "chat-prompt", **(data.metadata if data.metadata else {})}
#             )
# return message


def build_message_from_agent_response(data: BuildMessageFromAgentMetadata) -> str:
    if isinstance(data.response, Message):
        text_parts: List[str] = []
        for part in data.response.parts:
            if getattr(part.root, "kind", None) == "text":
                text_part = cast(TextPart, part.root)
                text_parts.append(text_part.text)
        return f"{data.card.name} says: {' '.join(text_parts)}"
    return f"{data.card.name} sent a non-text response."


## Advanced A2AClientPlugin
advanced_plugin = A2AClientPlugin(
    A2AClientPluginOptions(
        # Custom function metadata builder
        build_function_metadata=build_function_metadata,
        # Custom message builder - can return either Message or string
        build_message_for_agent=build_message_for_agent,
        # Custom response processor
        build_message_from_agent_response=build_message_from_agent_response,
    )
)
advanced_plugin.on_use_plugin(
    A2APluginUseParams(
        key="my-weather-agent", base_url=f"http://localhost:{PORT}/a2a", card_url=".well-known/agent-card.json"
    )
)
advanced_prompt = ChatPrompt(model=completions_model, plugins=[advanced_plugin])

# A2A Server Agent Card
agent_card = AgentCard(
    name="weather_agent",
    description="An agent that can tell you the weather",
    url=f"http://localhost:{PORT}/a2a/",
    version="0.0.1",
    protocol_version="0.3.0",
    capabilities=AgentCapabilities(),
    default_input_modes=[],
    default_output_modes=[],
    skills=[
        AgentSkill(
            # Expose various skills that this agent can perform
            id="get_weather",
            name="Get Weather",
            description="Get the weather for a given location",
            tags=["weather", "get", "location"],
            examples=[
                # Give concrete examples on how to contact the agent
                "Get the weather for London",
                "What is the weather",
                "What's the weather in Tokyo?",
                "How is the current temperature in San Francisco?",
            ],
        ),
    ],
)


# Define the parameter for A2AServer function
class LocationParams(BaseModel):
    location: str
    "The location to get the weather for"


# Setup the A2A Server Plugin
plugins: List[PluginBase] = [A2APlugin(A2APluginOptions(agent_card=agent_card)), DevToolsPlugin()]
app = App(logger=logger, plugins=plugins)


# A2A Server Event Handler
async def my_event_handler(user_message: str) -> Union[Message, str]:
    logger.info(f"Received message: {user_message}")
    tool_location = None

    async def location_handler(params: LocationParams) -> str:
        nonlocal tool_location
        tool_location = params.location
        return f"The weather in {params.location} is sunny"

    result = (
        await ChatPrompt(model=completions_model)
        .with_function(
            Function(
                name="location",
                description="The location to get the weather for",
                parameter_schema=LocationParams,
                handler=location_handler,
            )
        )
        .send(user_message, instructions="You are a weather agent that can tell you the weather for a given location")
    )

    if not tool_location:
        return Message(
            kind="message",
            message_id=str(uuid.uuid4()),
            role=Role("agent"),
            parts=[Part(root=TextPart(kind="text", text="Please provide a location"))],
        )
    else:
        return result.response.content if result.response.content else "No weather information available."


# A2A Server Message Event Handler
@app.event(A2AMessageEventKey)
async def handle_a2a_message(message: A2AMessageEvent) -> None:
    request_context = message.get("request_context")
    respond = message.get("respond")

    logger.info(f"Received message: {request_context.message}")

    if request_context.message:
        text_input = None
        for part in request_context.message.parts:
            if getattr(part.root, "kind", None) == "text":
                text_part = cast(TextPart, part.root)
                text_input = text_part.text
                break
        if not text_input:
            await respond("My agent currently only supports text input")
            return

        result = await my_event_handler(text_input)
        await respond(result)


async def handler(message: str) -> ModelMessage:
    # Now we can send the message to the prompt and it will decide if
    # the a2a agent should be used or not and also manages contacting the agent
    result = await prompt.send(message)
    return result.response


# A2A Client Message Handler
@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]):
    await ctx.reply(TypingActivityInput())

    result = await handler(ctx.activity.text)
    if result.content:
        await ctx.send(result.content)


if __name__ == "__main__":
    asyncio.run(app.start())
