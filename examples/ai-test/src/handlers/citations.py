"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from microsoft_teams.api import CitationAppearance, MessageActivity, MessageActivityInput
from microsoft_teams.apps import ActivityContext


async def handle_citations_demo(ctx: ActivityContext[MessageActivity]) -> None:
    """Demo citations functionality as shown in docs"""
    cited_docs = [
        {"title": "Weather Documentation", "content": "Weather data shows sunny conditions across the region"},
        {"title": "Pokemon Database", "content": "Comprehensive database of Pokemon characteristics and abilities"},
        {"title": "AI Development Guide", "content": "Best practices for integrating AI into Teams applications"},
    ]

    response_text = (
        "Here's some information with citations [1] about weather patterns,"
        "[2] Pokemon data, and [3] AI development best practices."
    )

    message_activity = MessageActivityInput(text=response_text).add_ai_generated()
    for i, doc in enumerate(cited_docs):
        message_activity.add_citation(i + 1, CitationAppearance(name=doc["title"], abstract=doc["content"]))

    await ctx.send(message_activity)
