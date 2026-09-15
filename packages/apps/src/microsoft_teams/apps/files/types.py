"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal

FileSource = Literal["botActivity", "graph"]
"""
Where the SDK found an inbound file.
- `botActivity` files come straight from the inbound activity's attachments;
- `graph` files are hydrated through Microsoft Graph.
"""
