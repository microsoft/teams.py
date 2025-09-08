import importlib.metadata
from typing import Annotated

from fastapi import Request
from microsoft.teams.api.auth.credentials import ClientCredentials, Credentials
from microsoft.teams.apps import Plugin, Sender
from microsoft.teams.apps.http_plugin import HttpPlugin
from microsoft.teams.apps.plugins.metadata import DependencyMetadata
from microsoft.teams.common.http.client import Client

from botbuilder.core import ActivityHandler, Bot
from botbuilder.integration.aiohttp import CloudAdapter, ConfigurationServiceClientCredentialFactory

version = importlib.metadata.version("microsoft-teams-botbuilder")


@Plugin(name="http", version=version, description="A plugin to use teams ai library with bot builder")
class BotbuilderPlugin(HttpPlugin, Sender):
    client: Annotated[Client, DependencyMetadata()]
    credentials: Annotated[Credentials | None, DependencyMetadata()]

    adapter: CloudAdapter

    def __init__(self, bot: Bot, adapter: CloudAdapter | None = None, handler: ActivityHandler | None = None):
        self.adapter = adapter
        self.bot = bot
        self.botbuilder_handler = handler

    async def on_init(self) -> None:
        await super().on_init()
        if self.adapter is None:
            client_id = self.credentials.client_id if self.credentials else None
            secret = (
                self.credentials.client_secret
                if self.credentials and isinstance(self.credentials, ClientCredentials)
                else None
            )
            tenant_id = (
                self.credentials.tenant_id
                if self.credentials and isinstance(self.credentials, ClientCredentials)
                else None
            )
            self.adapter = CloudAdapter(
                ConfigurationServiceClientCredentialFactory(
                    {
                        "APP_TYPE": "SingleTenant" if tenant_id is not None else "MultiTenant",
                        "APP_ID": client_id,
                        "APP_PASSWORD": secret,
                    }
                )
            )

    async def on_activity_request(self, request: Request, response: Response) -> Any:
        await self.adapter.process(request, self.bot)
        await super().on_activity_request(request, response)
