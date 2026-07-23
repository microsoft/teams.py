"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import argparse
import asyncio
import logging

from microsoft_teams.api import MessageActivityInput
from microsoft_teams.apps import App

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    parser = argparse.ArgumentParser(description="Send proactive messages using AgenticUser")
    parser.add_argument("conversation_id", help="The Teams conversation ID to send messages to")
    parser.add_argument("agent_app_instance_id", help="The AgentAppInstance client ID")
    parser.add_argument("agentic_user_id", help="The agentic user object ID")
    args = parser.parse_args()

    app = App()
    await app.initialize()

    agentic_user = app.get_agentic_user(args.agent_app_instance_id, args.agentic_user_id)
    sent = await app.send(
        args.conversation_id,
        "Hello from app.send with an AgenticUser.",
        agentic_user=agentic_user,
    )
    logger.info("Sent activity through app.send. Activity ID: %s", sent.id)

    api_sent = await app.api.from_agentic_user(agentic_user).conversations.create_activity(
        args.conversation_id,
        MessageActivityInput(text="Hello from the conversation activity API with an AgenticUser."),
    )
    logger.info("Sent activity through app.api. Activity ID: %s", api_sent.id)


if __name__ == "__main__":
    asyncio.run(main())
