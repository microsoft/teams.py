"""Integration tests for teams and reactions operations."""

import pytest

from microsoft_teams.api.activities import MessageActivityInput




class TestTeams:
    """Tests for team details and channels."""

    @pytest.mark.asyncio
    async def test_get_team_details(self, fixture):
        """Get details of the test team."""
        api = fixture.api
        team_id = fixture.config.team_id

        details = await api.teams.get_by_id(team_id)
        assert details.id is not None

    @pytest.mark.asyncio
    async def test_get_team_channels(self, fixture):
        """Get channels for the test team."""
        api = fixture.api
        team_id = fixture.config.team_id

        channels = await api.teams.get_conversations(team_id)
        assert len(channels) > 0


class TestReactions:
    """Tests for adding and removing reactions."""

    @pytest.mark.asyncio
    async def test_add_and_delete_reaction(self, fixture):
        """Add a reaction to an activity then remove it."""
        if fixture.is_agentic:
            pytest.skip("Reactions not supported with agentic identity")
        if fixture.is_canary:
            pytest.skip("Reactions return 404 on canary")

        api = fixture.api
        conv_id = fixture.config.conversation_id

        # Send a message to react to
        activity = MessageActivityInput().with_text("[PY Integration] reaction target")
        sent = await api.conversations.activities(conv_id).create(activity)

        # Add reaction
        await api.reactions.add(conv_id, sent.id, "like")

        # Remove reaction
        await api.reactions.delete(conv_id, sent.id, "like")
