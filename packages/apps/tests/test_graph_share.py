"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

# pyright: basic

import base64

from microsoft_teams.apps.files.graph_share import build_drive_item_content_url, encode_sharing_url


def _decode(token: str) -> str:
    """Reverse the u! transform, so a round-trip asserts the encoding rather than restating it."""
    body = token[2:].replace("_", "/").replace("-", "+")
    return base64.b64decode(body + "=" * (-len(body) % 4)).decode("utf-8")


class TestEncodeSharingUrl:
    def test_produces_the_documented_u_form(self):
        # The worked example from Graph's own documentation, which is the only place the full transform
        # (including the UTF-8 step) is spelled out.
        assert (
            encode_sharing_url("https://onedrive.live.com/redir?resid=1&authkey=!x")
            == "u!aHR0cHM6Ly9vbmVkcml2ZS5saXZlLmNvbS9yZWRpcj9yZXNpZD0xJmF1dGhrZXk9IXg"
        )

    def test_strips_base64_padding(self):
        assert "=" not in encode_sharing_url("https://a.example/b")

    def test_substitutes_both_base64url_characters(self):
        encoded = encode_sharing_url("https://example.com/~a?b=\u00ff\u00ff>?")
        assert "+" not in encoded
        assert "/" not in encoded

    def test_round_trips_non_ascii(self):
        # OneDrive paths embed the file name, so non-ASCII is routine rather than exotic. Encoding as latin-1
        # would silently corrupt these.
        url = "https://contoso.sharepoint.com/personal/a/Documents/rapport-caf\u00e9-caf\u00e9.pdf"
        assert _decode(encode_sharing_url(url)) == url

    def test_round_trips_a_url_containing_spaces(self):
        url = "https://contoso.sharepoint.com/personal/a/Documents/quarterly report.docx"
        assert _decode(encode_sharing_url(url)) == url


class TestSharedItemContentUrl:
    def test_appends_the_api_version(self):
        # The SDK passes a host root and the Graph client appends the version, so this path must append it too.
        assert build_drive_item_content_url("https://a.example/b", "https://graph.microsoft.com") == (
            f"https://graph.microsoft.com/v1.0/shares/{encode_sharing_url('https://a.example/b')}/driveItem/content"
        )

    def test_routes_to_the_sovereign_host(self):
        # GCCH's graph_scope is `https://graph.microsoft.us/.default`, so the derived root is a different host.
        assert build_drive_item_content_url("https://a.example/b", "https://graph.microsoft.us").startswith(
            "https://graph.microsoft.us/v1.0/shares/"
        )

    def test_defaults_to_the_public_cloud(self):
        assert build_drive_item_content_url("https://a.example/b").startswith(
            "https://graph.microsoft.com/v1.0/shares/"
        )

    def test_does_not_double_the_separator(self):
        assert "//v1.0" not in build_drive_item_content_url("https://a.example/b", "https://graph.microsoft.com/")
