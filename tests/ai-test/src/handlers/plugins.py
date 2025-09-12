"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from microsoft.teams.ai.message import Message
from microsoft.teams.ai.plugin import BaseAIPlugin
from pydantic import BaseModel


class LoggingAIPlugin(BaseAIPlugin):
    """Custom AI Plugin for logging and tracking function calls"""

    def __init__(self):
        super().__init__("logging_plugin")
        self.function_calls: list[str] = []

    async def on_before_function_call(self, function_name: str, args: BaseModel) -> None:
        print(f"[PLUGIN] About to call function: {function_name} with args: {args}")
        self.function_calls.append(function_name)

    async def on_after_function_call(self, function_name: str, args: BaseModel, result: str) -> str | None:
        print(f"[PLUGIN] Function {function_name} returned: {result}")
        return f"{result} (verified by logging plugin)"

    async def on_before_send(self, input: Message) -> Message | None:
        if hasattr(input, "content") and input.content:
            print(f"[PLUGIN] Processing input: {input.content[:50]}...")
        return None
