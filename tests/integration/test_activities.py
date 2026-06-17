"""Integration tests for activity operations (send, update, reply, delete)."""

from datetime import datetime, timezone

import pytest
from microsoft_teams.api.activities import MessageActivityInput


class TestActivities:
    """Tests for conversation activity CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_activity(self, fixture):
        """Send a message activity and verify it returns an ID."""
        api = fixture.api
        conv_id = fixture.config.conversation_id

        activity = MessageActivityInput().with_text(
            f"[PY Integration] create at {datetime.now(timezone.utc).isoformat()}"
        )
        result = await api.conversations.activities(conv_id).create(activity)
        assert result.id is not None
        assert result.id != "DO_NOT_USE_PLACEHOLDER_ID"

    @pytest.mark.asyncio
    async def test_update_activity(self, fixture):
        """Send then update an activity."""
        api = fixture.api
        conv_id = fixture.config.conversation_id

        activity = MessageActivityInput().with_text(
            f"[PY Integration] update-original at {datetime.now(timezone.utc).isoformat()}"
        )
        sent = await api.conversations.activities(conv_id).create(activity)

        updated = MessageActivityInput().with_text(
            f"[PY Integration] update-edited at {datetime.now(timezone.utc).isoformat()}"
        )
        result = await api.conversations.activities(conv_id).update(sent.id, updated)
        assert result.id is not None
        assert result.id != "DO_NOT_USE_PLACEHOLDER_ID"

    @pytest.mark.asyncio
    async def test_reply_to_activity(self, fixture):
        """Send a message then reply to it."""
        api = fixture.api
        conv_id = fixture.config.conversation_id

        original = MessageActivityInput().with_text(
            f"[PY Integration] reply-original at {datetime.now(timezone.utc).isoformat()}"
        )
        sent = await api.conversations.activities(conv_id).create(original)

        reply = MessageActivityInput().with_text(f"[PY Integration] reply at {datetime.now(timezone.utc).isoformat()}")
        result = await api.conversations.activities(conv_id).reply(sent.id, reply)
        assert result.id is not None
        assert result.id != "DO_NOT_USE_PLACEHOLDER_ID"

    @pytest.mark.asyncio
    async def test_delete_activity(self, fixture):
        """Send then delete an activity."""
        api = fixture.api
        conv_id = fixture.config.conversation_id

        activity = MessageActivityInput().with_text(
            f"[PY Integration] delete-me at {datetime.now(timezone.utc).isoformat()}"
        )
        sent = await api.conversations.activities(conv_id).create(activity)

        # Should not raise
        await api.conversations.activities(conv_id).delete(sent.id)
