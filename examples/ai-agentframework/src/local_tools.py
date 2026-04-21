"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
from os import getenv
from typing import Annotated

from agent_framework import tool
from azure.identity.aio import ClientSecretCredential
from dotenv import find_dotenv, load_dotenv
from msgraph import GraphServiceClient  # pyright: ignore[reportPrivateImportUsage]
from msgraph.generated.groups.groups_request_builder import (  # pyright: ignore[reportMissingTypeStubs]
    GroupsRequestBuilder,  # pyright: ignore[reportMissingTypeStubs]
)
from msgraph.generated.users.users_request_builder import UsersRequestBuilder  # pyright: ignore[reportMissingTypeStubs]
from pydantic import Field

load_dotenv(find_dotenv(usecwd=True))

_credential = ClientSecretCredential(
    tenant_id=getenv("TENANT_ID", ""),
    client_id=getenv("CLIENT_ID", ""),
    client_secret=getenv("CLIENT_SECRET", ""),
)
_graph = GraphServiceClient(credentials=_credential, scopes=["https://graph.microsoft.com/.default"])


def _person(user: object) -> dict[str, str]:
    return {
        "id": getattr(user, "id", None) or "",
        "name": getattr(user, "display_name", None) or "",
        "upn": getattr(user, "user_principal_name", None) or "",
        "email": getattr(user, "mail", None) or getattr(user, "user_principal_name", None) or "",
        "title": getattr(user, "job_title", None) or "",
        "department": getattr(user, "department", None) or "",
        "office": getattr(user, "office_location", None) or "",
    }


@tool
async def find_people(
    query: Annotated[str, Field(description="Name, email, job title, or department fragment")],
    limit: Annotated[int, Field(description="Max results", ge=1, le=25)] = 5,
) -> list[dict[str, str]] | str:
    """Search the org directory. Returns up to `limit` people with name, email, title, department, office."""
    safe = query.replace('"', "")
    params = UsersRequestBuilder.UsersRequestBuilderGetQueryParameters(
        search=f'"displayName:{safe}" OR "mail:{safe}" OR "jobTitle:{safe}" OR "department:{safe}"',
        select=["id", "displayName", "mail", "userPrincipalName", "jobTitle", "department", "officeLocation"],
        top=limit,
    )
    config = UsersRequestBuilder.UsersRequestBuilderGetRequestConfiguration(query_parameters=params)
    config.headers.add("ConsistencyLevel", "eventual")
    result = await _graph.users.get(request_configuration=config)
    if not result or not result.value:
        return f"No people found matching {query!r}."
    return [_person(u) for u in result.value]


@tool
async def get_org_context(
    user: Annotated[
        str,
        Field(description="User's Graph id (preferred), UPN, or email. Prefer the id from find_people results."),
    ],
) -> dict[str, object] | str:
    """Get a person's profile, their manager, and their direct reports in one call."""
    user_item = _graph.users.by_user_id(user)
    profile, manager, reports = await asyncio.gather(
        user_item.get(),
        user_item.manager.get(),
        user_item.direct_reports.get(),
        return_exceptions=True,
    )

    if isinstance(profile, BaseException) or not profile:
        return f"Could not get profile for {user!r}: {profile}"

    return {
        "profile": _person(profile),
        "manager": _person(manager) if manager and not isinstance(manager, BaseException) else None,
        "direct_reports": (
            [_person(u) for u in reports.value]  # type: ignore
            if reports and not isinstance(reports, BaseException) and getattr(reports, "value", None)
            else []
        ),
    }


@tool
async def list_team_members(
    team_or_group_name: Annotated[str, Field(description="Display name of a Team or M365 group")],
    limit: Annotated[int, Field(description="Max members to return", ge=1, le=50)] = 20,
) -> list[dict[str, str]] | str:
    """Resolve a Team/M365 group by display name and return its members."""
    safe = team_or_group_name.replace("'", "''")
    group_params = GroupsRequestBuilder.GroupsRequestBuilderGetQueryParameters(
        filter=f"displayName eq '{safe}'",
        select=["id", "displayName"],
        top=1,
    )
    group_config = GroupsRequestBuilder.GroupsRequestBuilderGetRequestConfiguration(query_parameters=group_params)
    groups = await _graph.groups.get(request_configuration=group_config)
    if not groups or not groups.value:
        return f"No group found with display name {team_or_group_name!r}."

    group_id = groups.value[0].id
    if not group_id:
        return f"Group {team_or_group_name!r} has no id."

    members = await _graph.groups.by_group_id(group_id).members.get()
    if not members or not members.value:
        return f"Group {team_or_group_name!r} has no members."

    return [_person(m) for m in members.value[:limit]]


@tool
async def get_presence(
    user: Annotated[
        str,
        Field(description="User's Graph id (preferred), UPN, or email. Prefer the id from find_people results."),
    ],
) -> dict[str, str] | str:
    """Get a person's current Teams presence (availability + activity)."""
    try:
        presence = await _graph.users.by_user_id(user).presence.get()
    except Exception as e:
        return f"Could not get presence for {user!r}: {e}"
    if not presence:
        return f"No presence information for {user!r}."
    return {
        "availability": presence.availability or "Unknown",
        "activity": presence.activity or "Unknown",
    }


tools = [find_people, get_org_context, list_team_members, get_presence]
