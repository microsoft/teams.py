"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import re
from os import getenv
from typing import Literal, cast

from approval import create_approval_function, create_approval_wrapped_function
from dotenv import find_dotenv, load_dotenv
from microsoft.teams.ai import ChatPrompt, Function, ListMemory
from microsoft.teams.api import MessageActivity, MessageActivityInput
from microsoft.teams.apps import ActivityContext, App
from microsoft.teams.devtools import DevToolsPlugin
from microsoft.teams.openai import OpenAICompletionsAIModel
from pydantic import BaseModel

load_dotenv(find_dotenv(usecwd=True))


app = App(plugins=[DevToolsPlugin()])


def get_required_env(key: str) -> str:
    value = getenv(key)
    if not value:
        raise ValueError(f"Required environment variable {key} is not set")
    return value


# Get OpenAI model (like in ai-test)
AZURE_OPENAI_MODEL = get_required_env("AZURE_OPENAI_MODEL")
ai_model = OpenAICompletionsAIModel(model=AZURE_OPENAI_MODEL)


class BuyStockParams(BaseModel):
    stock: str
    quantity: int


def create_buy_stock_function() -> Function[BuyStockParams]:
    """Create a buy stock function."""
    return Function(
        name="buy_stock",
        description="purchase stocks by specifying ticker symbol and quantity",
        parameter_schema=BuyStockParams,
        handler=lambda params: (
            f"✅ Successfully purchased {params.quantity} shares of {params.stock}. Order executed at market price."
        ),
    )


# Global memory instance
memory = ListMemory()

# Global mode flag
current_mode: Literal["wrapped", "separate", "simple"] = "simple"  # "wrapped" or "separate" or "simple"


# Handler for mode switching
@app.on_message_pattern(re.compile(r"^set\s+(wrapped|separate|simple)$", re.IGNORECASE))
async def handle_set_mode(ctx: ActivityContext[MessageActivity]) -> None:
    """Handle 'set <mode>' commands."""
    global current_mode
    global memory
    match = re.match(r"^set\s+(wrapped|separate|simple)$", ctx.activity.text, re.IGNORECASE)
    if match:
        mode = match.group(1).lower()
        current_mode = cast(Literal["wrapped", "separate", "simple"], mode)
        memory = ListMemory()
        await ctx.send(f"🔄 Switched to **{mode} {'approval' if mode == 'wrapped' else 'tools'}** mode")


@app.on_message_pattern(re.compile(r"^mode$", re.IGNORECASE))
async def handle_check_mode(ctx: ActivityContext[MessageActivity]) -> None:
    """Handle 'mode' command to check current mode."""
    await ctx.send(f"📋 Current mode: **{current_mode}**")


@app.on_message
async def handle_simple(ctx: ActivityContext[MessageActivity]) -> None:
    if current_mode != "simple":
        await ctx.next()
        return

    print(f"[SIMPLE] Message received: {ctx.activity.text}")

    stock_function = create_buy_stock_function()
    chat_prompt = ChatPrompt(
        instructions="You are a helpful assistant. Use the available stock trading tool when users want to buy stocks.",
        model=ai_model,
        functions=[stock_function],
        memory=memory,
    )
    result = await chat_prompt.send(ctx.activity.text)
    if result.response and result.response.content:
        await ctx.send(result.response.content)


# Handler for separate tools demo
@app.on_message
async def handle_separate_tools_demo(ctx: ActivityContext[MessageActivity]) -> None:
    """Demo showing separate tools pattern - approval tool + weather tool."""
    # Only handle if current mode is separate and this is a weather question
    if current_mode != "separate":
        await ctx.next()
        return

    print(f"[SEPARATE TOOLS] Message received: {ctx.activity.text}")

    try:
        # Create separate approval and stock functions
        approval_function = create_approval_function(ctx)
        stock_function = create_buy_stock_function()

        chat_prompt = ChatPrompt(
            instructions=(
                "You are a helpful assistant who always asks for approval"
                " before buying stocks. Use get_human_approval first, then use stock trading tools."
            ),
            model=ai_model,
            functions=[approval_function, stock_function],  # Two separate tools
            memory=memory,
        )

        # Handle deferred functions or normal chat
        if await chat_prompt.requires_resuming():
            chat_result = await chat_prompt.resume(ctx.activity)
        else:
            chat_result = await chat_prompt.send(input=ctx.activity.text)

        if chat_result.response and chat_result.response.content:
            message = MessageActivityInput(text=chat_result.response.content).add_ai_generated()
            await ctx.send(message)
        elif chat_result.is_deferred:
            # Approval message already sent by the handler
            pass

    except Exception as e:
        print(f"[SEPARATE TOOLS] Error: {str(e)}")
        await ctx.send(f"❌ Error: {str(e)}")


# Handler for wrapped approval demo
@app.on_message
async def handle_wrapped_approval_demo(ctx: ActivityContext[MessageActivity]) -> None:
    """Demo showing wrapped approval pattern - simple tool that requires approval."""
    # Only handle if current mode is wrapped and this is a weather question
    if current_mode != "wrapped":
        await ctx.next()
        return

    print(f"[WRAPPED APPROVAL] Message received: {ctx.activity.text}")

    try:
        # Create approval-wrapped stock function with custom approval message

        def custom_stock_approval(params: BuyStockParams) -> str:
            return (
                "📈 **Stock Purchase Approval Required**\n\n"
                "The agent wants to buy:\n"
                f"• Stock: **{params.stock}**\n"
                f"• Quantity: **{params.quantity} shares**\n\n"
                "⚠️ This will execute a market order which may"
                "involve significant financial risk.\n\n"
                "Approve this stock purchase? Say 'yes' or 'no'"
            )

        wrapped_stock_function = create_approval_wrapped_function(
            sender=ctx,
            original_function=create_buy_stock_function(),
            create_approval_message=custom_stock_approval,
        )

        chat_prompt = ChatPrompt(
            instructions=(
                "You are a helpful assistant. Use the available stock tradingtool when users want to buy stocks."
            ),
            model=ai_model,
            functions=[wrapped_stock_function],
            memory=memory,
        )

        # Handle deferred functions or normal chat
        if await chat_prompt.requires_resuming():
            chat_result = await chat_prompt.resume(ctx.activity)
        else:
            chat_result = await chat_prompt.send(input=ctx.activity.text)

        if chat_result.response and chat_result.response.content:
            message = MessageActivityInput(text=chat_result.response.content).add_ai_generated()
            await ctx.send(message)
        elif chat_result.is_deferred:
            # Approval message already sent by the handler
            pass

    except Exception as e:
        print(f"[WRAPPED APPROVAL] Error: {str(e)}")
        await ctx.send(f"❌ Error: {str(e)}")


if __name__ == "__main__":
    asyncio.run(app.start())
