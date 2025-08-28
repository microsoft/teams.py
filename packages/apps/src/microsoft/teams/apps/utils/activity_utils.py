"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from microsoft.teams.api import ActivityBase


def extract_tenant_id(activity: ActivityBase) -> Optional[str]:
    """
    Extract tenant ID from an activity with fallback logic.

    Attempts to extract tenant ID from multiple sources in the following order:
    1. activity.conversation.tenant_id (primary source)
    2. activity.tenant.id (fallback source from channel data)

    Args:
        activity: The activity to extract tenant ID from

    Returns:
        The tenant ID if found, None otherwise
    """
    tenant_id = None

    # Primary source: conversation.tenant_id
    if hasattr(activity, "conversation") and activity.conversation:
        tenant_id = getattr(activity.conversation, "tenant_id", None)

    # Fallback source: activity.tenant.id (from channel_data)
    if not tenant_id and hasattr(activity, "tenant"):
        tenant_info = getattr(activity, "tenant", None)
        if tenant_info and hasattr(tenant_info, "id"):
            tenant_id = tenant_info.id

    return tenant_id
