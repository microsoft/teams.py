"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import base64


def encode_sharing_url(url: str) -> str:
    """
    Encode a sharing URL as a Microsoft Graph sharing token, for `GET /shares/{token}/driveItem/...`.

    Graph's docs spell out base64, strip `=`, then swap `/`->`_` and `+`->`-`. `urlsafe_b64encode` does the swap
    but keeps padding, hence the `rstrip`.
    """
    return "u!" + base64.urlsafe_b64encode(url.encode("utf-8")).decode("ascii").rstrip("=")


def build_drive_item_content_url(sharing_url: str, base_url_root: str = "https://graph.microsoft.com") -> str:
    """
    Build the Graph endpoint that streams a drive item's bytes, reached by its sharing URL.

    `base_url_root` is a host root such as `https://graph.microsoft.com`, matching what `derive_graph_base_url`
    produces from the cloud's Graph scope. The API version is appended here because `get_graph_client` appends its
    own: a pre-versioned value produces `/v1.0/v1.0` and a bare host 404s in a way that reads like a
    missing item.
    """
    return f"{base_url_root.rstrip('/')}/v1.0/shares/{encode_sharing_url(sharing_url)}/driveItem/content"
