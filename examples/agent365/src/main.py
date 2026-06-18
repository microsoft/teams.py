"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import os

from dotenv import load_dotenv
from microsoft_teams.api import ClientCredentials
from microsoft_teams.apps.token_manager import AGENT_BOT_API_SCOPE, TokenManager


def get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"{name} must be set")

    return value


async def main():
    load_dotenv()

    tenant_id = get_required_env("AGENT365_TENANT_ID")
    blueprint_client_id = get_required_env("AGENT365_BLUEPRINT_CLIENT_ID")
    blueprint_client_secret = get_required_env("AGENT365_BLUEPRINT_CLIENT_SECRET")
    agentic_app_id = get_required_env("AGENT365_AGENTIC_APP_ID")
    agentic_user_id = os.getenv("AGENT365_AGENTIC_USER_ID")
    agentic_user_upn = os.getenv("AGENT365_AGENTIC_USER_UPN")
    scope = os.getenv("AGENT365_SCOPE", AGENT_BOT_API_SCOPE)

    credentials = ClientCredentials(
        client_id=blueprint_client_id,
        client_secret=blueprint_client_secret,
        tenant_id=tenant_id,
    )
    token_manager = TokenManager(credentials=credentials)

    token = await token_manager.get_agentic_token(
        tenant_id,
        agentic_app_id,
        scope,
        agentic_user_id=agentic_user_id,
        agentic_user_upn=agentic_user_upn,
    )

    print(f"Acquired agent user token for {scope}")
    print(f"Token preview: {str(token)[:20]}...")


if __name__ == "__main__":
    asyncio.run(main())
