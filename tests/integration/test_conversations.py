"""Integration tests for conversation creation (1:1 and group)."""

import pytest
from microsoft_teams.api.clients.conversation.params import CreateConversationParams
from microsoft_teams.api.models import Account


class TestConversations:
    """Tests for creating conversations."""

    @pytest.mark.asyncio
    async def test_create_personal_conversation(self, fixture):
        """Create a 1:1 conversation with a user."""
        api = fixture.api

        assert fixture.member_mri_1 is not None, "No cached members available"
        params = CreateConversationParams(
            members=[Account(id=fixture.member_mri_1)],
            tenant_id=fixture.config.tenant_id,
        )
        result = await api.conversations.create(params)
        assert result.id is not None
        assert result.id != ""

    @pytest.mark.asyncio
    async def test_create_group_conversation(self, fixture):
        """Create a group conversation with a single member + bot pattern."""
        api = fixture.api

        assert fixture.member_mri_1 is not None, "No cached members available"
        # Service rejects multiple members via Bot+Members pattern.
        # Use single non-bot member with channel_data containing tenant.
        params = CreateConversationParams(
            members=[Account(id=fixture.member_mri_1)],
            channel_data={"tenant": {"id": fixture.config.tenant_id}},
        )
        result = await api.conversations.create(params)
        assert result.id is not None
        assert result.id != ""
