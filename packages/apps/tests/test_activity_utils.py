"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from unittest.mock import MagicMock

from microsoft.teams.api.activities.message import MessageActivity
from microsoft.teams.api.models import Account, ConversationAccount
from microsoft.teams.apps.utils import extract_tenant_id


class TestActivityUtils:
    """Test activity utility functions."""

    def test_extract_tenant_id_from_conversation(self):
        """Test extracting tenant ID from conversation.tenant_id."""
        # Create an activity with tenant ID in conversation
        conversation = ConversationAccount(id="test-conversation", tenant_id="tenant-from-conversation")

        activity = MessageActivity(
            type="message",
            id="test-activity-id",
            text="hello",
            from_=Account(id="test-user", name="Test User"),
            recipient=Account(id="test-app", name="Test App"),
            conversation=conversation,
            channel_id="msteams",
        )

        tenant_id = extract_tenant_id(activity)
        assert tenant_id == "tenant-from-conversation"

    def test_extract_tenant_id_from_activity_tenant(self):
        """Test extracting tenant ID from activity.tenant when conversation.tenant_id is None."""
        # Create a mock activity to bypass property restrictions
        activity = MagicMock()

        # Set up conversation without tenant_id
        conversation = MagicMock()
        conversation.tenant_id = None
        activity.conversation = conversation

        # Set up tenant info
        tenant_info = MagicMock()
        tenant_info.id = "tenant-from-activity"
        activity.tenant = tenant_info

        tenant_id = extract_tenant_id(activity)
        assert tenant_id == "tenant-from-activity"

    def test_extract_tenant_id_priority_conversation_over_activity(self):
        """Test that conversation.tenant_id takes priority over activity.tenant.id."""
        # Create a mock activity with both sources
        activity = MagicMock()

        # Set up conversation with tenant_id (should take priority)
        conversation = MagicMock()
        conversation.tenant_id = "tenant-from-conversation"
        activity.conversation = conversation

        # Set up tenant info (should be ignored)
        tenant_info = MagicMock()
        tenant_info.id = "tenant-from-activity"
        activity.tenant = tenant_info

        tenant_id = extract_tenant_id(activity)
        assert tenant_id == "tenant-from-conversation"

    def test_extract_tenant_id_no_tenant_available(self):
        """Test that None is returned when no tenant ID is available."""
        # Create a mock activity with no tenant information
        activity = MagicMock()

        # Set up conversation without tenant_id
        conversation = MagicMock()
        conversation.tenant_id = None
        activity.conversation = conversation

        # Remove tenant attribute to simulate no tenant property
        del activity.tenant

        tenant_id = extract_tenant_id(activity)
        assert tenant_id is None

    def test_extract_tenant_id_no_conversation(self):
        """Test behavior when activity has no conversation."""
        # Create a mock activity without conversation
        activity = MagicMock()
        activity.conversation = None

        # Remove tenant attribute
        del activity.tenant

        tenant_id = extract_tenant_id(activity)
        assert tenant_id is None

    def test_extract_tenant_id_tenant_without_id(self):
        """Test behavior when activity.tenant exists but has no id."""
        # Create a mock activity
        activity = MagicMock()

        # Set up conversation without tenant_id
        conversation = MagicMock()
        conversation.tenant_id = None
        activity.conversation = conversation

        # Set up tenant info without id attribute
        tenant_info = MagicMock()
        del tenant_info.id  # Remove id attribute
        activity.tenant = tenant_info

        tenant_id = extract_tenant_id(activity)
        assert tenant_id is None
