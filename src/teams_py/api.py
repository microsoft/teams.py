"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import os
from typing import Optional

from dotenv import load_dotenv
from microsoft.teams.api import (
    Account,
    Activity,
    BotClient,
    ClientCredentials,
    ConversationClient,
    CreateConversationParams,
    GetConversationsParams,
)
from microsoft.teams.common.http import ClientOptions

# Load environment variables from .env file
load_dotenv()


class TeamsApiTester:
    """Test the Teams API clients."""

    def __init__(self, service_url: str, token: str) -> None:
        """Initialize the tester.

        Args:
            service_url: The Teams service URL.
            token: The authentication token.
        """
        options = ClientOptions(
            headers={"Authorization": f"Bearer {token}"},
        )
        self.client = ConversationClient(service_url, options)

    async def test_conversation_client(self, conversation_id: Optional[str] = None) -> None:
        """Test the conversation client.

        Args:
            conversation_id: Optional conversation ID to use for testing. If not provided,
                           a new conversation will be created.
        """
        print("\nTesting Conversation Client...")

        # Get conversations
        print("\nGetting conversations...")
        try:
            conversations = await self.client.get(GetConversationsParams())
            print(f"Found {len(conversations.conversations)} conversations")
            if conversations.conversations:
                print("First conversation:")
                print(f"  ID: {conversations.conversations[0].id}")
                print(f"  Type: {conversations.conversations[0].type}")
                print(f"  Is Group: {conversations.conversations[0].is_group}")
        except Exception as e:
            print(f"Error getting conversations: {e}")

        # Create a conversation if no ID provided
        if not conversation_id:
            print("\nCreating a new conversation...")
            try:
                conversation = await self.client.create(
                    CreateConversationParams(
                        is_group=True,
                        members=[
                            Account(id="user1", name="User 1"),
                            Account(id="user2", name="User 2"),
                        ],
                        topic_name="Test Conversation",
                    )
                )
                conversation_id = conversation.id
                print(f"Created conversation with ID: {conversation_id}")
            except Exception as e:
                print(f"Error creating conversation: {e}")
                return

        if not conversation_id:
            print("No conversation ID available for testing")
            return

        # Test activities
        print("\nTesting activities...")
        try:
            activities = self.client.activities(conversation_id)

            # Create an activity
            activity = await activities.create(Activity(type="message", text="Hello from Python SDK!"))
            print(f"Created activity with ID: {activity.id}")

            # Update the activity
            updated = await activities.update(
                activity.id,
                Activity(type="message", text="Updated message from Python SDK!"),
            )
            print(f"Updated activity: {updated.text}")

            # Reply to the activity
            reply = await activities.reply(
                activity.id,
                Activity(type="message", text="Reply from Python SDK!"),
            )
            print(f"Replied to activity: {reply.text}")

            # Get members for the activity
            activity_members = await activities.get_members(activity.id)
            print(f"Activity has {len(activity_members)} members")

            # Delete the activity
            await activities.delete(activity.id)
            print("Deleted activity")
        except Exception as e:
            print(f"Error testing activities: {e}")

        # Test members
        print("\nTesting members...")
        try:
            members = self.client.members(conversation_id)

            # Get all members
            all_members = await members.get_all()
            print(f"Conversation has {len(all_members)} members")
            for member in all_members:
                print(f"  Member: {member.name} (ID: {member.id})")

            # Get a specific member
            if all_members:
                member = await members.get(all_members[0].id)
                print(f"Got member: {member.name} (ID: {member.id})")
        except Exception as e:
            print(f"Error testing members: {e}")


async def main() -> None:
    """Run the API tests."""
    # Get configuration from environment
    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")
    tenant_id = os.getenv("TENANT_ID")
    service_url = os.getenv("TEAMS_SERVICE_URL")
    conversation_id = os.getenv("TEAMS_CONVERSATION_ID")

    if not client_id or not client_secret:
        print("Error: CLIENT_ID and CLIENT_SECRET environment variables must be set")
        print("Please copy .env.example to .env and fill in your values")
        return

    # Create bot client and get token
    bot_client = BotClient()
    credentials = ClientCredentials(
        client_id=client_id,
        client_secret=client_secret,
        tenant_id=tenant_id,
    )

    try:
        token_response = await bot_client.token.get(credentials)
    except Exception as e:
        print(f"Error getting bot token: {e}")
        print("Please check your CLIENT_ID and CLIENT_SECRET in the .env file")
        return

    if not service_url:
        print("Warning: TEAMS_SERVICE_URL not set, using default")
        service_url = "https://smba.trafficmanager.net/teams"

    # Create tester and run tests
    tester = TeamsApiTester(service_url, token_response.access_token)
    await tester.test_conversation_client(conversation_id)


if __name__ == "__main__":
    asyncio.run(main())
