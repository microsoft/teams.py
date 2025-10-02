"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import TYPE_CHECKING, Any, Awaitable, Callable, List, Optional, TypedDict, Union

from fastapi import Request

from .auth import remote_function_jwt_validation
from .contexts import FunctionContext

if TYPE_CHECKING:
    from . import App
from .manifest import (
    CommandListScope,
    ConfigurableTab,
    ConfigurableTabContext,
    ConfigurableTabScope,
    MeetingSurface,
    StaticTab,
    StaticTabContext,
    SupportedSharePointHost,
)


class StaticTabOptions(TypedDict, total=False):
    contentBotId: str
    context: List[StaticTabContext]
    name: str
    scopes: List[CommandListScope]
    searchUrl: str
    websiteUrl: str


class ConfigurableTabOptions(TypedDict, total=False):
    canUpdateConfiguration: bool
    context: List[ConfigurableTabContext]
    meetingSurfaces: List[MeetingSurface]
    scopes: List[ConfigurableTabScope]
    sharePointPreviewImage: str
    supportedSharePointHosts: List[SupportedSharePointHost]


class AppEmbed:
    def __init__(self, app: "App"):
        self.app = app

    def tab(self, name: str, path: str, options: Optional[StaticTabOptions] = None) -> None:
        """
        Add/update a static tab.
        The tab will be hosted at
        http://localhost:<PORT>/tabs/<name> or https://<BOT_DOMAIN>/tabs/<name>
        Scopes default to 'personal'.

        Args:
            name A unique identifier for the entity which the tab displays.
            path The path to the web `dist` folder.
        """

        static_tabs: List[StaticTab] = self.app._manifest.get("staticTabs", [])  # pyright: ignore[reportPrivateUsage]
        i = next((idx for idx, t in enumerate(static_tabs) if t.get("entityId") == name), -1)

        tab: StaticTab = {
            "entityId": name,
            "contentUrl": f"https://${{BOT_DOMAIN}}/tabs/{name}",
            "scopes": ["personal"],
            **(options or {}),
        }

        if i > -1:
            static_tabs[i] = tab
        else:
            static_tabs.append(tab)

        self.app._manifest["staticTabs"] = static_tabs  # pyright: ignore[reportPrivateUsage]

        self.app.page(f"/tabs/{name}/", dir_path=path, page_path=f"/tabs/{name}/")

        return None

    def config_tab(self, url: str, options: Optional[ConfigurableTabOptions] = None) -> None:
        """
        Add a configurable tab.
        Scopes default to 'team'.

        Args:
            url The url to use when configuring the tab.
        """
        configurable_tabs: List[ConfigurableTab] = self.app._manifest.get("configurableTabs", [])  # pyright: ignore[reportPrivateUsage]
        tab: ConfigurableTab = {
            "configurationUrl": url,
            "scopes": ["team"],
            **(options or {}),
        }
        configurable_tabs.append(tab)
        self.app._manifest["configurableTabs"] = configurable_tabs  # pyright: ignore[reportPrivateUsage]

    def func(self, name: str, cb: Callable[[FunctionContext[Any]], Union[Any, Awaitable[Any]]]) -> None:
        """
        Add/update a function that can be called remotely.

        Args:
            name: The unique function name.
            cb: The callback to handle the function.
        """

        log = self.app.log.getChild("functions").getChild(name)

        validator = self.app.entra_token_validator

        async def endpoint(req: Request):
            # Run through JWT validation middleware manually
            middleware = remote_function_jwt_validation(validator, log)

            async def call_next(r: Request):
                ctx = FunctionContext(app=self.app, log=log, data=await req.json(), **req.state.context)
                return await cb(ctx)

            return await middleware(req, call_next)

        # Register the endpoint
        self.app.http.post(f"/api/functions/{name}")(endpoint)

        return None
