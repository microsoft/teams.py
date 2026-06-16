"""
Integration test fixture for Microsoft Teams Python SDK.

Provides shared authentication and configuration for all integration tests.
Uses azure-identity for token acquisition and caches conversation
members to avoid 429 throttling.
"""

import os
from dataclasses import dataclass, field
from typing import Optional

import pytest_asyncio
from azure.identity.aio import ClientSecretCredential
from dotenv import load_dotenv
from microsoft_teams.api import ApiClient
from microsoft_teams.common.http import Client, ClientOptions


@dataclass
class TestConfig:
    tenant_id: str
    client_id: str
    client_secret: str
    service_url: str
    conversation_id: str
    user_id: str
    team_id: str
    channel_id: str
    meeting_id: str
    user_id_2: Optional[str] = None
    agentic_app_id: Optional[str] = None
    agentic_user_id: Optional[str] = None
    scope: str = "https://api.botframework.com/.default"


@dataclass
class TestFixture:
    config: TestConfig
    api: ApiClient
    credential: ClientSecretCredential
    cached_members: list = field(default_factory=list)
    member_mri_1: Optional[str] = None
    member_mri_2: Optional[str] = None

    @property
    def is_canary(self) -> bool:
        return "canary" in self.config.service_url.lower()

    @property
    def is_agentic(self) -> bool:
        return self.config.agentic_app_id is not None and self.config.agentic_app_id != ""


# Module-level cache (persists across tests in the same process)
_cached_config: Optional[TestConfig] = None
_cached_members: Optional[list] = None
_cached_member_mri_1: Optional[str] = None
_cached_member_mri_2: Optional[str] = None


def _load_config() -> TestConfig:
    """Load test configuration from environment variables."""
    global _cached_config
    if _cached_config is not None:
        return _cached_config

    test_dir = os.path.dirname(os.path.abspath(__file__))
    for env_file in [".env.botid-prod", ".env"]:
        env_path = os.path.join(test_dir, env_file)
        if os.path.exists(env_path):
            load_dotenv(env_path)
            break

    def env(name: str, fallback: Optional[str] = None) -> str:
        value = os.environ.get(name, fallback)
        if not value:
            raise RuntimeError(f"Missing required env var: {name}")
        return value

    _cached_config = TestConfig(
        tenant_id=env("AZURE_TENANT_ID"),
        client_id=env("AZURE_CLIENT_ID"),
        client_secret=env("AZURE_CLIENT_SECRET"),
        service_url=env("TEST_SERVICE_URL"),
        conversation_id=env("TEST_CONVERSATION_ID"),
        user_id=env("TEST_USER_ID"),
        team_id=env("TEST_TEAM_ID"),
        channel_id=env("TEST_CHANNEL_ID"),
        meeting_id=env("TEST_MEETING_ID"),
        user_id_2=os.environ.get("TEST_USER_ID_2"),
        agentic_app_id=os.environ.get("TEST_AGENTIC_APP_ID"),
        agentic_user_id=os.environ.get("TEST_AGENTIC_USER_ID"),
        scope=os.environ.get("AZURE_SCOPE", "https://api.botframework.com/.default"),
    )
    return _cached_config


@pytest_asyncio.fixture
async def fixture():
    """Per-test fixture — creates a fresh credential + client on the current event loop."""
    global _cached_members, _cached_member_mri_1, _cached_member_mri_2

    config = _load_config()

    credential = ClientSecretCredential(
        tenant_id=config.tenant_id,
        client_id=config.client_id,
        client_secret=config.client_secret,
    )

    async def token_factory() -> str:
        t = await credential.get_token(config.scope)
        return t.token

    http_client = Client(ClientOptions(token=token_factory))
    api = ApiClient(service_url=config.service_url, options=http_client)

    f = TestFixture(config=config, api=api, credential=credential)

    # Cache members once (avoids 429 throttling)
    if _cached_members is None:
        members = await api.conversations.members(config.conversation_id).get_all()
        bot_prefix = f"28:{config.client_id}"
        _cached_members = [m for m in members if m.id and not m.id.startswith(bot_prefix)]
        if _cached_members:
            _cached_member_mri_1 = _cached_members[0].id
        if len(_cached_members) > 1:
            _cached_member_mri_2 = _cached_members[1].id

    f.cached_members = _cached_members or []
    f.member_mri_1 = _cached_member_mri_1
    f.member_mri_2 = _cached_member_mri_2

    yield f

    await credential.close()
