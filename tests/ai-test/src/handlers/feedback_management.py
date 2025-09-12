"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List

from microsoft.teams.api.activities.invoke.message.submit_action import MessageSubmitActionInvokeActivity
from microsoft.teams.apps import ActivityContext


@dataclass
class StoredFeedback:
    """Data structure for storing feedback information"""

    message_id: str
    likes: int = 0
    dislikes: int = 0
    feedbacks: List[Dict[str, Any]] = field(default_factory=lambda: [])


# Global storage for feedback (in production, use proper storage)
stored_feedback_by_message_id: Dict[str, StoredFeedback] = {}


def initialize_feedback_storage(message_id: str) -> StoredFeedback:
    """Initialize feedback storage for a message"""
    feedback = StoredFeedback(message_id=message_id)
    stored_feedback_by_message_id[message_id] = feedback
    return feedback


def get_feedback_storage(message_id: str) -> StoredFeedback | None:
    """Get feedback storage for a message"""
    return stored_feedback_by_message_id.get(message_id)


async def handle_feedback_submission(ctx: ActivityContext[MessageSubmitActionInvokeActivity]) -> None:
    """Handle feedback submission event"""
    activity = ctx.activity
    logger = logging.getLogger(__name__)

    # Extract feedback data from activity value
    if not hasattr(activity, "value") or not activity.value:
        logger.warning(f"No value found in activity {activity.id}")
        return

    # Type-safe access to activity value
    value_dict = activity.value.model_dump() if hasattr(activity.value, "model_dump") else {}
    action_value: Dict[str, Any] = value_dict.get("actionValue", {})
    reaction: str | None = action_value.get("reaction")
    feedback_str: str | None = action_value.get("feedback")
    assert feedback_str, "No feedback string found in action_value"
    feedback_json: Dict[str, Any] = json.loads(feedback_str)

    if not activity.reply_to_id:
        logger.warning(f"No replyToId found for messageId {activity.id}")
        return

    existing_feedback = get_feedback_storage(activity.reply_to_id)

    if not existing_feedback:
        new_feedback = StoredFeedback(message_id=activity.reply_to_id)
        stored_feedback_by_message_id[activity.reply_to_id] = new_feedback
        existing_feedback = new_feedback

    # Update feedback counts and store text feedback
    likes_increment = 1 if reaction == "like" else 0
    dislikes_increment = 1 if reaction == "dislike" else 0

    updated_feedback = StoredFeedback(
        message_id=existing_feedback.message_id,
        likes=existing_feedback.likes + likes_increment,
        dislikes=existing_feedback.dislikes + dislikes_increment,
        feedbacks=[*existing_feedback.feedbacks, feedback_json],
    )

    stored_feedback_by_message_id[activity.reply_to_id] = updated_feedback

    # Send confirmation response
    feedback_text: str = feedback_json.get("feedbackText", "")
    reaction_text: str = f" and {reaction}" if reaction else ""
    text_part: str = f" with comment: '{feedback_text}'" if feedback_text else ""

    await ctx.reply(f"✅ Thank you for your feedback{reaction_text}{text_part}!")


def get_feedback_summary(message_id: str) -> str:
    """Get a summary of feedback for a message"""
    feedback = get_feedback_storage(message_id)
    if not feedback:
        return "No feedback collected yet."

    total_reactions = feedback.likes + feedback.dislikes
    comments_count = len([f for f in feedback.feedbacks if f.get("feedbackText")])

    summary_parts: List[str] = []
    if total_reactions > 0:
        summary_parts.append(f"👍 {feedback.likes} likes, 👎 {feedback.dislikes} dislikes")
    if comments_count > 0:
        summary_parts.append(f"💬 {comments_count} comments")

    return " | ".join(summary_parts) if summary_parts else "No feedback collected yet."
