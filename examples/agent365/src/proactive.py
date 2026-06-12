"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

# Agent 365 Proactive Example
# ===========================
# This example sends proactive messages from a specific AgentUserIdentity.

import argparse
import asyncio
import logging

from microsoft_teams.apps import App
from microsoft_teams.cards import ActionSet, AdaptiveCard, ExecuteAction, SubmitData, TextBlock

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def send_proactive_message(
    app: App,
    conversation_id: str,
    agent_identity_app_id: str,
    agent_user_id: str,
    message: str,
) -> None:
    """Send a proactive message from an AgentUserIdentity."""
    agent_user_identity = app.get_agent_user_identity(agent_identity_app_id, agent_user_id)
    logger.info(f"Sending proactive message as agent user: {agent_user_identity.id}")
    logger.info(f"Message: {message}")
    result = await app.send(conversation_id, agent_user_identity, message)

    logger.info(f"Message sent successfully. Activity ID: {result.id}")


async def send_proactive_card(
    app: App,
    conversation_id: str,
    agent_identity_app_id: str,
    agent_user_id: str,
) -> None:
    """Send a proactive Adaptive Card from an AgentUserIdentity."""
    agent_user_identity = app.get_agent_user_identity(agent_identity_app_id, agent_user_id)
    card = AdaptiveCard(
        schema="http://adaptivecards.io/schemas/adaptive-card.json",
        body=[
            TextBlock(text="Agent 365 Notification", size="Large", weight="Bolder"),
            TextBlock(text="This message was sent proactively from an AgentUserIdentity.", wrap=True),
            TextBlock(text=f"Agent user: {agent_user_identity.id}", wrap=True, is_subtle=True),
            ActionSet(
                actions=[
                    ExecuteAction(title="Acknowledge")
                    .with_data(SubmitData("ack_agent365_card", {"agent_user_id": agent_user_identity.id}))
                    .with_associated_inputs("auto")
                ]
            ),
        ],
    )

    logger.info(f"Sending proactive card as agent user: {agent_user_identity.id}")

    result = await app.send(conversation_id, agent_user_identity, card)

    logger.info(f"Card sent successfully. Activity ID: {result.id}")


async def main():
    parser = argparse.ArgumentParser(description="Send proactive messages from an Agent 365 AgentUserIdentity")
    parser.add_argument("conversation_id", help="The Teams conversation ID to send messages to")
    parser.add_argument("agent_identity_app_id", help="The concrete agent identity app/client ID")
    parser.add_argument("agent_user_id", help="The agent user object ID")
    args = parser.parse_args()

    app = App()

    logger.info("Initializing app without starting server...")
    await app.initialize()
    logger.info("App initialized")

    await send_proactive_message(
        app,
        args.conversation_id,
        args.agent_identity_app_id,
        args.agent_user_id,
        "Hello! This is a proactive message sent from an AgentUserIdentity.",
    )

    await asyncio.sleep(2)

    await send_proactive_card(
        app,
        args.conversation_id,
        args.agent_identity_app_id,
        args.agent_user_id,
    )

    logger.info("All proactive AgentUserIdentity messages sent successfully")


if __name__ == "__main__":
    asyncio.run(main())
