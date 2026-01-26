"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.

Proactive Messaging Example
===========================
This example demonstrates how to send proactive messages to Teams users
without running a server. This is useful for:
- Scheduled notifications
- Alert systems
- Background jobs that need to notify users
- Webhook handlers that send messages

Key points:
- Uses app.initialize() instead of app.start() (no HTTP server)
- Directly sends messages using app.send()
- Requires a conversation ID (from previous interactions or from the Teams API)
"""

import argparse
import asyncio

from microsoft_teams.apps import App
from microsoft_teams.cards import ActionSet, AdaptiveCard, OpenUrlAction, TextBlock


async def send_proactive_message(app: App, conversation_id: str, message: str) -> None:
    """
    Send a proactive message to a Teams conversation.

    Args:
        app: The initialized App instance
        conversation_id: The Teams conversation ID to send the message to
        message: The message text to send
    """
    print(f"Sending proactive message to conversation: {conversation_id}")
    print(f"Message: {message}")

    # Send the message
    result = await app.send(conversation_id, message)

    print(f"✓ Message sent successfully! Activity ID: {result.id}")


async def send_proactive_card(app: App, conversation_id: str) -> None:
    """
    Send a proactive Adaptive Card to a Teams conversation.

    Args:
        app: The initialized App instance
        conversation_id: The Teams conversation ID to send the card to
    """
    # Create an Adaptive Card
    card = AdaptiveCard(
        schema="http://adaptivecards.io/schemas/adaptive-card.json",
        body=[
            TextBlock(text="Proactive Notification", size="Large", weight="Bolder"),
            TextBlock(text="This message was sent proactively without a server running!", wrap=True),
            TextBlock(text="Status: Active • Priority: High • Time: Now", wrap=True, is_subtle=True),
            ActionSet(actions=[OpenUrlAction(title="Learn More", url="https://aka.ms/teams-sdk")]),
        ],
    )

    print(f"Sending proactive card to conversation: {conversation_id}")

    result = await app.send(conversation_id, card)

    print(f"✓ Card sent successfully! Activity ID: {result.id}")


async def main():
    """
    Main function demonstrating proactive messaging.

    In a real application, you would:
    1. Store conversation IDs when users first interact with your bot
    2. Use those IDs later to send proactive messages
    3. Get conversation IDs from the Teams API or from previous interactions
    """
    parser = argparse.ArgumentParser(
        description="Send proactive messages to a Teams conversation without running a server"
    )
    parser.add_argument("conversation_id", help="The Teams conversation ID to send messages to")
    args = parser.parse_args()

    # Create app (no plugins needed for sending only)
    app = App()

    # Initialize the app without starting the HTTP server
    # This sets up credentials, token manager, and activity sender
    print("Initializing app (without starting server)...")
    await app.initialize()
    print("✓ App initialized\n")

    # Example 1: Send a simple text message
    await send_proactive_message(
        app, args.conversation_id, "Hello! This is a proactive message sent without a running server 🚀"
    )

    # Wait a bit between messages
    await asyncio.sleep(2)

    # Example 2: Send an Adaptive Card
    await send_proactive_card(app, args.conversation_id)

    print("\n✓ All proactive messages sent successfully!")


if __name__ == "__main__":
    asyncio.run(main())
