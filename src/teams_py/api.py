"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import argparse
import asyncio
import os

from microsoft.teams.api import ConversationActivityClient, ConversationMemberClient
from microsoft.teams.api.models import Activity
from microsoft.teams.common.http import Client, ClientOptions


class TeamsApiTester:
    """Helper class to test Teams API clients."""

    def __init__(self, service_url: str, http_client: Client):
        """Initialize the tester with service URL and HTTP client."""
        self.service_url = service_url
        self.http_client = http_client
        self.member_client = ConversationMemberClient(service_url, http_client)
        self.activity_client = ConversationActivityClient(service_url, http_client)

    async def test_member_client(self, conversation_id: str) -> None:
        """Test the member client functionality."""
        print("\n=== Testing Member Client ===")

        try:
            # Test getting all members
            print("\nGetting all members...")
            members = await self.member_client.get(conversation_id)
            print(f"Found {len(members)} members:")
            for member in members:
                print(f"- {member.name} (ID: {member.id}, Role: {member.role})")
                if member.aad_object_id:
                    print(f"  AAD Object ID: {member.aad_object_id}")
                if member.properties:
                    print(f"  Properties: {member.properties}")

            # Test getting a specific member if we have any
            if members:
                member_id = members[0].id
                print(f"\nGetting member {member_id}...")
                member = await self.member_client.get_by_id(conversation_id, member_id)
                print(f"Found member: {member.name} (ID: {member.id}, Role: {member.role})")

        except Exception as e:
            print(f"Error testing member client: {e}")
            raise

    async def test_activity_client(self, conversation_id: str) -> None:
        """Test the activity client functionality."""
        print("\n=== Testing Activity Client ===")

        try:
            # Test creating a new activity
            print("\nCreating a new activity...")
            activity = Activity(
                type="message",
                text="Hello from Teams Python SDK!",
                properties={"test": True},
            )
            created_activity = await self.activity_client.create(conversation_id, activity)
            print(f"Created activity: {created_activity.text} (ID: {created_activity.id})")

            # Test updating the activity
            print("\nUpdating the activity...")
            created_activity.text = "Updated message from Teams Python SDK!"
            updated_activity = await self.activity_client.update(conversation_id, created_activity.id, created_activity)
            print(f"Updated activity: {updated_activity.text}")

            # Test replying to the activity
            print("\nReplying to the activity...")
            reply = Activity(
                type="message",
                text="This is a reply from Teams Python SDK!",
            )
            reply_activity = await self.activity_client.reply(conversation_id, created_activity.id, reply)
            print(f"Created reply: {reply_activity.text}")

            # Test getting members for the activity
            print("\nGetting members for the activity...")
            activity_members = await self.activity_client.get_members(conversation_id, created_activity.id)
            print(f"Found {len(activity_members)} members for the activity:")
            for member in activity_members:
                print(f"- {member.name} (ID: {member.id})")

            # Test deleting the activity
            print("\nDeleting the activity...")
            await self.activity_client.delete(conversation_id, created_activity.id)
            print("Activity deleted successfully")

        except Exception as e:
            print(f"Error testing activity client: {e}")
            raise


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Test Teams API clients with provided credentials and conversation ID."
    )
    parser.add_argument(
        "--token",
        required=True,
        help="Teams API token (can also be set via TEAMS_TOKEN environment variable)",
    )
    parser.add_argument(
        "--conversation-id",
        required=True,
        help="Conversation ID to test with (can also be set via TEAMS_CONVERSATION_ID environment variable)",
    )
    parser.add_argument(
        "--service-url",
        help="Teams service URL (can also be set via TEAMS_SERVICE_URL environment variable)",
        default="https://smba.trafficmanager.net/amer/3abdf8e8-c644-4510-9b59-2557b14ed67f",
    )
    return parser.parse_args()


async def main() -> None:
    """Main entry point for testing the Teams API clients."""
    # Parse command line arguments
    args = parse_args()

    # Get configuration from args or environment variables
    service_url: str = args.service_url or os.getenv("TEAMS_SERVICE_URL", args.service_url)
    token: str = args.token or os.getenv("TEAMS_TOKEN")
    conversation_id: str = args.conversation_id or os.getenv("TEAMS_CONVERSATION_ID")

    # Validate required parameters
    if not token:
        raise ValueError("Teams API token is required. Provide it via --token or TEAMS_TOKEN environment variable.")
    if not conversation_id:
        raise ValueError(
            "Conversation ID is required. Provide it via --conversation-id or TEAMS_CONVERSATION_ID env variable."
        )

    # Create HTTP client with options
    http_client = Client(
        ClientOptions(
            headers={
                "User-Agent": "TeamsPythonSDK/0.1.0",
            },
            token=token,
        )
    )

    # Create tester and run tests
    tester = TeamsApiTester(service_url, http_client)
    try:
        await tester.test_member_client(conversation_id)
        await tester.test_activity_client(conversation_id)
        print("\n=== All tests completed successfully! ===")
    except Exception as e:
        print(f"\n=== Test failed: {e} ===")
        raise


if __name__ == "__main__":
    asyncio.run(main())
