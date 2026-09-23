"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

# pyright: basic

from microsoft_teams.apps.files.errors import FileUrlExpiredError


class TestExpiredUrlGuidance:
    def test_first_fetch_states_the_url_cannot_be_renewed_and_offers_no_remedy(self):
        message = str(FileUrlExpiredError("first_fetch"))

        assert "not available via the SDK" not in message
        assert "Files.Read.All" not in message
        assert "Graph" not in message
        assert "sent again" in message

    def test_reread_still_points_at_reusing_the_downloaded_file(self):
        message = str(FileUrlExpiredError("reread"))

        assert "DownloadedFile" in message
        assert "Files.Read.All" not in message
