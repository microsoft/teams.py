"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
from os import getenv

from approval_for_function import ApprovalPlugin
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

    def handler(params: BuyStockParams) -> str:
        print("Actually running the buy stock fn")
        return f"✅ Successfully purchased {params.quantity} shares of {params.stock}. Order executed at market price."

    return Function(
        name="buy_stock",
        description="purchase stocks by specifying ticker symbol and quantity",
        parameter_schema=BuyStockParams,
        handler=handler,
    )


# Global memory instance
memory = ListMemory()


@app.on_message
async def handle_stock_trading(ctx: ActivityContext[MessageActivity]) -> None:
    """Handle stock trading with approval using ApprovalPlugin."""
    print(f"[STOCK TRADING] Message received: {ctx.activity.text}")

    try:
        # Create stock function (will be wrapped by plugin)
        stock_function = create_buy_stock_function()

        # Create approval plugin with fn_names to wrap
        approval_plugin = ApprovalPlugin(sender=ctx, functions=[stock_function])

        chat_prompt = ChatPrompt(
            instructions=(
                "You are a helpful assistant. Use the available stock trading tool when users want to buy stocks."
            ),
            model=ai_model,
            functions=[stock_function],  # Plugin will wrap this function
            memory=memory,
        ).with_plugin(approval_plugin)

        # Handle deferred functions or normal chat
        if await chat_prompt.requires_resuming():
            chat_result = await chat_prompt.resume(ctx.activity)
        else:
            chat_result = await chat_prompt.send(input=ctx.activity.text)

        if chat_result.response and chat_result.response.content:
            message = MessageActivityInput(text=chat_result.response.content).add_ai_generated()
            await ctx.send(message)
        elif chat_result.is_deferred:
            # Approval message already sent by the plugin
            pass

    except Exception as e:
        print(f"[STOCK TRADING] Error: {str(e)}")
        await ctx.send(f"❌ Error: {str(e)}")


if __name__ == "__main__":
    asyncio.run(app.start())
