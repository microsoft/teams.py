"""
Test script to verify graph clients integration in ActivityContext.
"""

import asyncio
import sys
from unittest.mock import MagicMock

# Add the app package to the path so we can import it
sys.path.append("packages/app/src")
sys.path.append("packages/api/src")
sys.path.append("packages/common/src")
sys.path.append("packages/graph/src")

from microsoft.teams.api import ApiClient, ConversationReference, JsonWebToken, MessageActivity
from microsoft.teams.api.models.account import ChannelAccount
from microsoft.teams.api.models.conversation import Conversation
from microsoft.teams.app.routing.activity_context import ActivityContext
from microsoft.teams.common import ConsoleLogger, LocalStorage


def create_mock_activity():
    """Create a mock MessageActivity for testing."""
    activity = MessageActivity(
        id="test-activity-123",
        type="message",
        text="Hello, test!",
        from_=ChannelAccount(id="user-123", name="Test User"),
        recipient=ChannelAccount(id="bot-456", name="Test Bot"),
        conversation=Conversation(id="conv-789", is_group=False),
        channel_id="channel-abc",
        service_url="https://test.service.url",
    )
    return activity


def create_mock_conversation_ref():
    """Create a mock ConversationReference."""
    return ConversationReference(
        service_url="https://test.service.url",
        activity_id="test-activity-123",
        bot=ChannelAccount(id="bot-456", name="Test Bot"),
        channel_id="channel-abc",
        conversation=Conversation(id="conv-789"),
        user=ChannelAccount(id="user-123", name="Test User"),
    )


async def test_graph_clients():
    """Test that graph clients are properly created and accessible."""
    print("🧪 Testing Graph Clients Integration...")

    # Create mock components
    activity = create_mock_activity()
    logger = ConsoleLogger().create_logger("test")
    storage = LocalStorage()
    api_client = MagicMock(spec=ApiClient)
    conversation_ref = create_mock_conversation_ref()

    # Create mock tokens
    user_token = JsonWebToken("mock-user-token-eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIs...")
    app_token = JsonWebToken("mock-app-token-eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIs...")

    # Test 1: ActivityContext with user signed in and app token available
    print("\n📝 Test 1: User signed in + App token available")
    ctx = ActivityContext(
        activity=activity,
        app_id="test-app-id",
        logger=logger,
        storage=storage,
        api=api_client,
        user_token=user_token,
        conversation_ref=conversation_ref,
        is_signed_in=True,
        connection_name="graph",
        app_token=app_token,
    )

    # Check if graph client properties are accessible
    print(f"   ✅ User signed in: {ctx.is_signed_in}")
    print(f"   ✅ Has user token: {ctx.user_token is not None}")
    print(f"   ✅ Has app token: {ctx._app_token is not None}")

    # Test user_graph property
    try:
        user_graph = ctx.user_graph
        print(f"   ✅ User graph client created: {user_graph is not None}")
        print(f"   ✅ User graph type: {type(user_graph).__name__}")
    except Exception as e:
        print(f"   ❌ Error creating user graph client: {e}")

    # Test app_graph property
    try:
        app_graph = ctx.app_graph
        print(f"   ✅ App graph client created: {app_graph is not None}")
        print(f"   ✅ App graph type: {type(app_graph).__name__}")
    except Exception as e:
        print(f"   ❌ Error creating app graph client: {e}")

    # Test 2: ActivityContext with user not signed in
    print("\n📝 Test 2: User NOT signed in")
    ctx_no_signin = ActivityContext(
        activity=activity,
        app_id="test-app-id",
        logger=logger,
        storage=storage,
        api=api_client,
        user_token=None,
        conversation_ref=conversation_ref,
        is_signed_in=False,
        connection_name="graph",
        app_token=app_token,
    )

    user_graph_no_signin = ctx_no_signin.user_graph
    app_graph_with_app_token = ctx_no_signin.app_graph

    print(f"   ✅ User graph (no signin): {user_graph_no_signin is None}")
    print(f"   ✅ App graph (with app token): {app_graph_with_app_token is not None}")

    # Test 3: ActivityContext with no app token
    print("\n📝 Test 3: No app token available")
    ctx_no_app_token = ActivityContext(
        activity=activity,
        app_id="test-app-id",
        logger=logger,
        storage=storage,
        api=api_client,
        user_token=user_token,
        conversation_ref=conversation_ref,
        is_signed_in=True,
        connection_name="graph",
        app_token=None,
    )

    user_graph_with_user_token = ctx_no_app_token.user_graph
    app_graph_no_token = ctx_no_app_token.app_graph

    print(f"   ✅ User graph (with user token): {user_graph_with_user_token is not None}")
    print(f"   ✅ App graph (no app token): {app_graph_no_token is None}")

    print("\n🎉 All tests completed!")


if __name__ == "__main__":
    asyncio.run(test_graph_clients())
