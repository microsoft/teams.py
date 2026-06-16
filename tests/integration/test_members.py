"""Integration tests for member operations (get all, get by ID, get paged)."""

import pytest




class TestMembers:
    """Tests for conversation member operations."""

    @pytest.mark.asyncio
    async def test_get_all_members(self, fixture):
        """Get all members of a conversation."""
        api = fixture.api
        conv_id = fixture.config.conversation_id

        members = await api.conversations.members(conv_id).get_all()
        assert len(members) > 0
        assert members[0].id is not None

    @pytest.mark.asyncio
    async def test_get_member_by_id(self, fixture):
        """Get a specific member by their MRI."""
        api = fixture.api
        conv_id = fixture.config.conversation_id

        assert fixture.member_mri_1 is not None, "No cached members available"
        member = await api.conversations.members(conv_id).get(fixture.member_mri_1)
        assert member.id == fixture.member_mri_1

    @pytest.mark.asyncio
    async def test_get_paged_members(self, fixture):
        """Get members with paging."""
        if fixture.is_canary or fixture.is_agentic:
            pytest.skip("Paged members not supported on canary/agentic")

        api = fixture.api
        conv_id = fixture.config.conversation_id

        result = await api.conversations.members(conv_id).get_paged(page_size=2)
        assert result.members is not None
        assert len(result.members) > 0
