"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from microsoft_teams.apps import DownloadedFile, IncomingFile
from microsoft_teams.cards import AdaptiveCard, Container, Fact, FactSet, TextBlock


def unsupported_file_card(file: IncomingFile, downloaded: DownloadedFile) -> AdaptiveCard:
    """
    FILE RECEIVE: the no-LLM response for a file this sample will not send to the model.

    Nothing here touches Azure OpenAI. It reports what the file API exposes (`scope`, `source`, resolved content type)
    plus the byte count that was actually downloaded, so the file round-trip is still demonstrated for formats the
    model never sees.
    """
    return AdaptiveCard(
        body=[
            Container(
                style="emphasis",
                items=[
                    TextBlock(text="File received", weight="Bolder", size="Large", color="Accent"),
                    TextBlock(text=downloaded.filename, weight="Bolder", wrap=True),
                ],
            ),
            FactSet(
                facts=[
                    Fact(title="Type", value=downloaded.content_type),
                    Fact(title="Size", value=_human_size(len(downloaded.bytes))),
                    Fact(title="Scope", value=file.scope),
                    Fact(title="Source", value=file.source),
                ]
            ),
            TextBlock(
                text=(
                    "I downloaded this file but did not analyze it. This sample sends only text files and PNG, JPEG, "
                    "GIF, or WebP images to the model."
                ),
                wrap=True,
                is_subtle=True,
                spacing="Medium",
            ),
        ]
    )


def _human_size(num_bytes: int) -> str:
    if num_bytes < 1024:
        return f"{num_bytes} B"
    units = ["KB", "MB", "GB"]
    value = num_bytes / 1024
    unit = 0
    while value >= 1024 and unit < len(units) - 1:
        value /= 1024
        unit += 1
    return f"{value:.1f} {units[unit]}"
