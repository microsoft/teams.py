"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from microsoft.teams.ai import Agent, ListMemory
from microsoft.teams.ai.ai_model import AIModel
from microsoft.teams.api import MessageActivity, MessageActivityInput
from microsoft.teams.apps import ActivityContext

# Simple in-memory store for conversation histories
# In your application, it may be a good idea to use a more
# persistent store backed by a database or other storage solution
conversation_store: dict[str, ListMemory] = {}


def get_or_create_conversation_memory(conversation_id: str) -> ListMemory:
    """Get or create conversation memory for a specific conversation"""
    if conversation_id not in conversation_store:
        conversation_store[conversation_id] = ListMemory()
    return conversation_store[conversation_id]


async def handle_stateful_conversation(model: AIModel, ctx: ActivityContext[MessageActivity]) -> None:
    """Example of stateful conversation handler that maintains conversation history"""
    print(f"Received message: {ctx.activity.text}")

    # Retrieve existing conversation memory or initialize new one
    memory = get_or_create_conversation_memory(ctx.activity.conversation.id)

    # Get existing messages for logging
    existing_messages = await memory.get_all()
    print(f"Existing messages before sending to prompt: {len(existing_messages)} messages")

    # Create agent with conversation-specific memory
    agent = Agent(model, memory=memory)

    chat_result = await agent.send(
        input=ctx.activity.text, instructions="You are a helpful assistant that remembers our previous conversation."
    )

    if chat_result.response.content:
        message = MessageActivityInput(text=chat_result.response.content).add_ai_generated()
        await ctx.send(message)
    else:
        await ctx.reply("I did not generate a response.")

    # Log final message count
    final_messages = await memory.get_all()
    print(f"Messages after sending to prompt: {len(final_messages)} messages")


async def clear_conversation_memory(conversation_id: str) -> None:
    """Clear memory for a specific conversation"""
    if conversation_id in conversation_store:
        memory = conversation_store[conversation_id]
        await memory.set_all([])
        print(f"Cleared memory for conversation {conversation_id}")
