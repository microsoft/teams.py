"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

# pyright: basic

from typing import Optional

import pytest
from microsoft_teams.api.activities.utils.strip_mentions_text import (
    StripMentionsTextOptions,
    strip_mentions_text,
)
from microsoft_teams.api.models import Account, ClientInfoEntity, MentionEntity


class FakeActivity:
    """Minimal object satisfying TextActivityProtocol for testing."""

    def __init__(self, text: Optional[str], entities=None):
        self.text = text
        self.entities = entities


def _mention(account_id: str, name: str, text: Optional[str] = None) -> MentionEntity:
    return MentionEntity(mentioned=Account(id=account_id, name=name), text=text)


@pytest.mark.unit
class TestStripMentionsText:
    def test_no_text_returns_none(self) -> None:
        activity = FakeActivity(text=None)
        assert strip_mentions_text(activity) is None  # type: ignore[arg-type]

    def test_empty_text_returns_none(self) -> None:
        activity = FakeActivity(text="")
        assert strip_mentions_text(activity) is None  # type: ignore[arg-type]

    def test_text_with_no_entities(self) -> None:
        activity = FakeActivity(text="Hello world", entities=None)
        assert strip_mentions_text(activity) == "Hello world"  # type: ignore[arg-type]

    def test_text_with_non_mention_entity_is_ignored(self) -> None:
        """Non-MentionEntity objects in entities list should not affect output."""
        client_info = ClientInfoEntity(locale="en-US")
        activity = FakeActivity(text="Hello world", entities=[client_info])
        assert strip_mentions_text(activity) == "Hello world"  # type: ignore[arg-type]

    def test_account_id_filter_skips_non_matching_mention(self) -> None:
        mention = _mention("bot-id", "My Bot", text="<at>My Bot</at>")
        activity = FakeActivity(
            text="Hello <at>My Bot</at>! How are you?",
            entities=[mention],
        )
        opts = StripMentionsTextOptions(account_id="other-id")
        result = strip_mentions_text(activity, opts)  # type: ignore[arg-type]
        # Mention for a different account should be left intact
        assert "<at>My Bot</at>" in result  # type: ignore[operator]

    def test_mention_with_name_only_is_stripped(self) -> None:
        """Mention has no .text but has .mentioned.name — uses name-based tag removal."""
        mention = _mention("bot-id", "My Bot", text=None)
        activity = FakeActivity(
            text="Hello <at>My Bot</at>!",
            entities=[mention],
        )
        result = strip_mentions_text(activity)  # type: ignore[arg-type]
        assert result == "Hello !"

    def test_mention_with_name_only_tag_only_mode(self) -> None:
        """tag_only=True keeps the inner text when removing via name-based tag."""
        mention = _mention("bot-id", "My Bot", text=None)
        activity = FakeActivity(
            text="Hello <at>My Bot</at>!",
            entities=[mention],
        )
        opts = StripMentionsTextOptions(tag_only=True)
        result = strip_mentions_text(activity, opts)  # type: ignore[arg-type]
        assert result == "Hello My Bot!"
