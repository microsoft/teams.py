"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import importlib.metadata
from dataclasses import dataclass
from logging import Logger
from typing import Annotated, Optional

from fastapi import Request
from microsoft.teams.api import Credentials
from microsoft.teams.apps import (
    DependencyMetadata,
    HttpPlugin,
    LoggerDependencyOptions,
    Plugin,
)
from pydantic import BaseModel

from botbuilder.core import ActivityHandler, TurnContext  # pyright: ignore[reportMissingTypeStubs]
from botbuilder.integration.aiohttp import (  # pyright: ignore[reportMissingTypeStubs]
    CloudAdapter,
    ConfigurationBotFrameworkAuthentication,
    ConfigurationServiceClientCredentialFactory,
)
from botbuilder.schema import Activity  # pyright: ignore[reportMissingTypeStubs]

version = importlib.metadata.version("microsoft-teams-botbuilder")


class BotBuilderPluginOptions(BaseModel):
    """Options for configuring the BotBuilder plugin."""

    skip_auth: bool = False
    handler: Optional[ActivityHandler] = None
    adapter: Optional[CloudAdapter] = None


@dataclass
class BotFrameworkConfig:
    APP_TYPE: str
    APP_ID: Optional[str]
    APP_PASSWORD: Optional[str]
    APP_TENANTID: Optional[str]


@Plugin(name="botbuilder-plugin", version=version)
class BotBuilderPlugin(HttpPlugin):
    """
    BotBuilder plugin that provides Microsoft Bot Framework integration.

    This plugin extends HttpPlugin and provides Bot Framework capabilities
    including CloudAdapter integration and activity handling.
    """

    # Dependency injections using type annotations
    logger: Annotated[Logger, LoggerDependencyOptions()]

    credentials: Annotated[Optional[Credentials], DependencyMetadata(optional=True)]

    def __init__(self, options: Optional[BotBuilderPluginOptions] = None):
        """
        Initialize the BotBuilder plugin.

        Args:
            options: Configuration options for the plugin
        """
        self.options = options or BotBuilderPluginOptions()

        # Initialize HttpPlugin
        super().__init__(
            app_id=self.credentials.client_id if self.credentials else None,
            skip_auth=self.options.skip_auth,
        )

        self.handler: Optional[ActivityHandler] = self.options.handler
        self.adapter: Optional[CloudAdapter] = self.options.adapter

    async def on_init(self) -> None:
        """Initialize the plugin when the app starts."""
        await super().on_init()

        if not self.adapter:
            # Extract credentials for Bot Framework authentication
            client_id: Optional[str] = None
            client_secret: Optional[str] = None
            tenant_id: Optional[str] = None

            if self.credentials:
                client_id = getattr(self.credentials, "client_id", None)
                client_secret = getattr(self.credentials, "client_secret", None)
                tenant_id = getattr(self.credentials, "tenant_id", None)

            config = BotFrameworkConfig(
                APP_TYPE="SingleTenant" if tenant_id else "MultiTenant",
                APP_ID=client_id,
                APP_PASSWORD=client_secret,
                APP_TENANTID=tenant_id,
            )

            self.adapter = CloudAdapter(
                ConfigurationBotFrameworkAuthentication(
                    ConfigurationServiceClientCredentialFactory(config, logger=self.logger)
                )
            )

        self.logger.info("BotBuilder plugin initialized successfully")

    async def on_request(self, request: Request):
        if not self.adapter:
            raise RuntimeError("plugin not registered")

        # Parse activity data
        body = await request.json()

        activity_type = body.get("type", "unknown")
        activity_id = body.get("id", "unknown")

        self.logger.debug(f"Received activity: {activity_type} (ID: {activity_id})")

        activity: Activity = Activity().deserialize(body)  # type: ignore

        async def logic(turn_context: TurnContext):
            if not turn_context.activity.id:
                return

            if self.handler:
                await self.handler.on_turn(turn_context)
            return

        auth_header = request.headers.get("Authorization", "")
        await self.adapter.process_activity(auth_header, activity, logic)  # type: ignore
