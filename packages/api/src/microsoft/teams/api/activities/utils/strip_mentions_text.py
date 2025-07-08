"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import List, Optional

from ...models import MentionEntity
from ..protocols import TextActivityProtocol


class StripMentionsTextOptions:
    """Options for stripping mentions from text"""

    def __init__(self, account_id: Optional[str] = None, tag_only: bool = False):
        """
        Args:
            account_id: The account to remove mentions for.
                       By default, all at-mentions listed in `entities` are removed.
            tag_only: When `True`, the inner text of the tag will not be removed.
                     Eg. input: Hello <at>my-bot</at>! How are you?
                         output: Hello my-bot! How are you?
        """
        self.account_id = account_id
        self.tag_only = tag_only


def strip_mentions_text(
    activity: TextActivityProtocol, options: Optional[StripMentionsTextOptions] = None
) -> Optional[str]:
    """
    Remove "<at>...</at>" text from an activity

    Args:
        activity: The activity containing text and entities
        options: Configuration options for stripping mentions

    Returns:
        The text with mentions stripped, or None if no text
    """
    if not activity.text:
        return None

    if options is None:
        options = StripMentionsTextOptions()

    text = activity.text

    # Get mention entities
    mentions: List[MentionEntity] = []
    if activity.entities:
        for entity in activity.entities:
            # Handle only mention entities
            if isinstance(entity, MentionEntity):
                mentions.append(entity)

    for mention in mentions:
        # Extract mention data based on type (dict or object)
        mentioned_id = mention.mentioned.id
        mentioned_name = mention.mentioned.name
        mention_text = mention.text

        # Skip if filtering by account_id and this mention doesn't match
        if options.account_id and mentioned_id != options.account_id:
            continue

        # Remove the mention from text
        if mention_text:
            text_without_tags = mention_text.replace("<at>", "").replace("</at>", "")
            replacement = text_without_tags if options.tag_only else ""
            text = text.replace(mention_text, replacement)
        elif mentioned_name:
            mention_tag = f"<at>{mentioned_name}</at>"
            replacement = mentioned_name if options.tag_only else ""
            text = text.replace(mention_tag, replacement)

    return text.strip()
