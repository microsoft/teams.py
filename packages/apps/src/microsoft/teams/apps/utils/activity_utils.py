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
    conversation = getattr(activity, "conversation", None)
    if conversation:
        tenant_id = getattr(conversation, "tenant_id", None)
        if tenant_id:
            return tenant_id

    tenant = getattr(activity, "tenant", None)
    if tenant:
        return getattr(tenant, "id", None)

    return None
