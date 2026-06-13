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
    parser = argparse.ArgumentParser(description="Send a proactive message using API-level AgenticIdentity")
    parser.add_argument("conversation_id", help="The Teams conversation ID to send messages to")
    parser.add_argument("agentic_app_id", help="The concrete agent identity app/client ID")
    parser.add_argument("agentic_user_id", help="The agent user object ID")
    args = parser.parse_args()

    app = App()
    await app.initialize()

    agentic_identity = app.get_agentic_identity(args.agentic_app_id, args.agentic_user_id)
    activity = MessageActivityInput(text="Hello from an API-level AgenticIdentity.")

    result = await app.api.conversations.activities(args.conversation_id).create(
        activity,
        agentic_identity=agentic_identity,
    )

    logger.info("Sent activity as agentic identity. Activity ID: %s", result.id)


if __name__ == "__main__":
    asyncio.run(main())
