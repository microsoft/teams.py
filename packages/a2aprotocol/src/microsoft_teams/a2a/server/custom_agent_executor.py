"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import uuid
from typing import Awaitable, Callable, TypedDict, Union

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import Message, Part, Role, Task, TextPart

type Respond = Callable[[Union[str, Message, Task]], Awaitable[None]]

# This key MUST be used for A2A message events.
A2AMessageEventKey = "a2a:message"


class A2AMessageEvent(TypedDict):
    request_context: RequestContext
    respond: Respond


class CustomAgentExecutor(AgentExecutor):
    def __init__(self, plugin_event: Callable[[str, A2AMessageEvent], Awaitable[None]]):
        super().__init__()
        self.plugin_event = plugin_event

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        response_future: asyncio.Future[None] = asyncio.Future()

        async def Respond(message: Union[str, Message, Task]) -> None:
            nonlocal response_future
            response_message: Union[Message, Task]

            if isinstance(message, str):
                response_message = Message(
                    kind="message",
                    message_id=str(uuid.uuid4()),
                    role=Role("agent"),
                    parts=[Part(root=TextPart(kind="text", text=message))],
                    # Associate the response with the incoming request's context.
                    context_id=context.context_id,
                )
            else:
                response_message = message

            await event_queue.enqueue_event(response_message)
            response_future.set_result(None)

        ctx: A2AMessageEvent = {
            "request_context": context,
            "respond": Respond,
        }

        if callable(self.plugin_event):
            await self.plugin_event(A2AMessageEventKey, ctx)
            await response_future

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        pass
