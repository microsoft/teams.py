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

AttachmentStyle = Literal["file", "inlineImage"]
"""
How a file was attached to the inbound message.
- `file`: sent as a file attachment
- `inlineImage`: pasted into the message body

Some image formats, such as BMP and AVIF, cannot be converted by the platform, so Teams shows a placeholder, and
they cannot be downloaded.
The same image sent as a file attachment downloads normally.
"""
