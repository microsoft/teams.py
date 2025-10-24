"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import pytest

from microsoft.teams.api.models.attachment import AttachmentLayout


class TestAttachmentLayout:
    """Test suite for AttachmentLayout enum."""

    def test_attachment_layout_has_list(self):
        """Test that AttachmentLayout has LIST value."""
        assert hasattr(AttachmentLayout, "LIST")
        assert AttachmentLayout.LIST == "list"

    def test_attachment_layout_has_grid(self):
        """Test that AttachmentLayout has GRID value."""
        assert hasattr(AttachmentLayout, "GRID")
        assert AttachmentLayout.GRID == "grid"

    def test_attachment_layout_values(self):
        """Test that AttachmentLayout has the correct values."""
        values = [layout.value for layout in AttachmentLayout]
        assert "list" in values
        assert "grid" in values
        assert len(values) == 2

    def test_attachment_layout_does_not_have_carousel(self):
        """Test that AttachmentLayout no longer has CAROUSEL value."""
        assert not hasattr(AttachmentLayout, "CAROUSEL")
        values = [layout.value for layout in AttachmentLayout]
        assert "carousel" not in values
