"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Dict, List, Union

from microsoft.teams.api import Account, Message
from microsoft.teams.cards import AdaptiveCard

IMAGE_URL = "https://github.com/microsoft/teams-agent-accelerator-samples/raw/main/python/memory-sample-agent/docs/images/memory-thumbnail.png"


def create_card(data: Dict[str, str]) -> AdaptiveCard:
    """Create an adaptive card from form data."""
    return AdaptiveCard(
        **{
            "type": "AdaptiveCard",
            "version": "1.4",
            "body": [
                {"type": "Image", "url": IMAGE_URL},
                {
                    "type": "TextBlock",
                    "text": data.get("title", ""),
                    "size": "Large",
                    "weight": "Bolder",
                    "color": "Accent",
                    "style": "heading",
                },
                {
                    "type": "TextBlock",
                    "text": data.get("subTitle", ""),
                    "size": "Small",
                    "weight": "Lighter",
                    "color": "Good",
                },
                {"type": "TextBlock", "text": data.get("text", ""), "wrap": True, "spacing": "Medium"},
            ],
        }
    )


def create_message_details_card(message_payload: Message) -> AdaptiveCard:
    """Create a card showing message details."""
    body: List[Dict[str, Union[str, bool]]] = [
        {
            "type": "TextBlock",
            "text": "Message Details",
            "size": "Large",
            "weight": "Bolder",
            "color": "Accent",
            "style": "heading",
        }
    ]

    if message_payload.body and message_payload.body.content:
        content_blocks: List[Dict[str, Union[str, bool]]] = [
            {"type": "TextBlock", "text": "Content", "size": "Medium", "weight": "Bolder", "spacing": "Medium"},
            {"type": "TextBlock", "text": message_payload.body.content},
        ]
        body.extend(content_blocks)

    if message_payload.attachments:
        attachment_blocks: List[Dict[str, Union[str, bool]]] = [
            {"type": "TextBlock", "text": "Attachments", "size": "Medium", "weight": "Bolder", "spacing": "Medium"},
            {
                "type": "TextBlock",
                "text": f"Number of attachments: {len(message_payload.attachments)}",
                "wrap": True,
                "spacing": "Small",
            },
        ]
        body.extend(attachment_blocks)

    if message_payload.created_date_time:
        date_blocks: List[Dict[str, Union[str, bool]]] = [
            {"type": "TextBlock", "text": "Created Date", "size": "Medium", "weight": "Bolder", "spacing": "Medium"},
            {"type": "TextBlock", "text": message_payload.created_date_time, "wrap": True, "spacing": "Small"},
        ]
        body.extend(date_blocks)

    if message_payload.link_to_message:
        link_blocks: List[Dict[str, Union[str, bool]]] = [
            {"type": "TextBlock", "text": "Message Link", "size": "Medium", "weight": "Bolder", "spacing": "Medium"}
        ]
        body.extend(link_blocks)

        actions = [{"type": "Action.OpenUrl", "title": "Go to message", "url": message_payload.link_to_message}]
    else:
        actions = []

    return AdaptiveCard(**{"type": "AdaptiveCard", "version": "1.4", "body": body, "actions": actions})


def create_conversation_members_card(members: List[Account]) -> AdaptiveCard:
    """Create a card showing conversation members."""
    members_list = ", ".join(member.name for member in members if member.name)

    return AdaptiveCard(
        **{
            "type": "AdaptiveCard",
            "version": "1.4",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "Conversation members",
                    "size": "Medium",
                    "weight": "Bolder",
                    "color": "Accent",
                    "style": "heading",
                },
                {"type": "TextBlock", "text": members_list, "wrap": True, "spacing": "Small"},
            ],
        }
    )


async def create_dummy_cards(search_query: str) -> List[Dict[str, Any]]:
    """Create dummy cards for search results."""
    dummy_items = [
        {
            "title": "Item 1",
            "description": f"This is the first item and this is your search query: {search_query}",
        },
        {"title": "Item 2", "description": "This is the second item"},
        {"title": "Item 3", "description": "This is the third item"},
        {"title": "Item 4", "description": "This is the fourth item"},
        {"title": "Item 5", "description": "This is the fifth item"},
    ]

    cards: List[Dict[str, Any]] = []
    for item in dummy_items:
        card_data: Dict[str, Any] = {
            "card": AdaptiveCard(
                **{
                    "type": "AdaptiveCard",
                    "version": "1.4",
                    "body": [
                        {
                            "type": "TextBlock",
                            "text": item["title"],
                            "size": "Large",
                            "weight": "Bolder",
                            "color": "Accent",
                            "style": "heading",
                        },
                        {"type": "TextBlock", "text": item["description"], "wrap": True, "spacing": "Medium"},
                    ],
                }
            ),
            "thumbnail": {
                "title": item["title"],
                "text": item["description"],
            },
        }
        cards.append(card_data)

    return cards


def create_link_unfurl_card(url: str) -> Dict[str, Any]:
    """Create a card for link unfurling."""
    thumbnail = {
        "title": "Unfurled Link",
        "text": url,
        "images": [{"url": IMAGE_URL}],
    }

    card = AdaptiveCard(
        **{
            "type": "AdaptiveCard",
            "version": "1.4",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "Unfurled Link",
                    "size": "Large",
                    "weight": "Bolder",
                    "color": "Accent",
                    "style": "heading",
                },
                {"type": "TextBlock", "text": url, "size": "Small", "weight": "Lighter", "color": "Good"},
            ],
        }
    )

    return {"card": card, "thumbnail": thumbnail}
