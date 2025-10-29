"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from logging import Logger
from typing import Annotated, Any, Awaitable, Callable, List, Optional

from microsoft.teams.apps import (
    DependencyMetadata,
    EventMetadata,
    HttpPlugin,
    LoggerDependencyOptions,
    Plugin,
    PluginBase,
)

from a2a.server.agent_execution import AgentExecutor
from a2a.server.apps import A2AFastAPIApplication
from a2a.server.request_handlers import DefaultRequestHandler, RequestHandler
from a2a.server.tasks import InMemoryTaskStore, TaskStore
from a2a.types import AgentCard
from a2a.utils.constants import AGENT_CARD_WELL_KNOWN_PATH

from .a2a_plugin_options import A2APluginOptions
from .custom_agent_executor import A2AMessageEvent, CustomAgentExecutor
from .logging_middleware import LoggingMiddleware


@Plugin(name="a2a", version="0.3.7", description="A2A Server Plugin")
class A2APlugin(PluginBase):
    logger: Annotated[Logger, LoggerDependencyOptions()]
    http: Annotated[HttpPlugin, DependencyMetadata()]

    emit: Annotated[Callable[[str, A2AMessageEvent], Awaitable[None]], EventMetadata(name="custom")]

    card: AgentCard
    path: str
    agent_card_path: str
    task_store: TaskStore
    custom_executor: Optional[AgentExecutor] = None
    _middlewares: List[Any] = []

    def __init__(self, options: A2APluginOptions):
        super().__init__()

        self.card = options.agent_card

        if options.path:
            self.path = options.path if options.path.startswith("/") else f"/{options.path}"

        self.agent_card_path = options.agent_card_path if options.agent_card_path else AGENT_CARD_WELL_KNOWN_PATH
        self.task_store = options.task_store if options.task_store else InMemoryTaskStore()
        self.custom_executor = options.agent_executor

    def use(self, middleware: Any, **kwargs: Any) -> None:
        """Add a middleware to the A2A plugin.

        Args:
            middleware: Either a middleware class (inheriting from BaseHTTPMiddleware)
                       or a dispatch function
            **kwargs: Additional keyword arguments to pass to the middleware constructor
        """
        self._middlewares.append((middleware, kwargs))

    async def on_init(self) -> None:
        a2a_app = A2AFastAPIApplication(agent_card=self.card, http_handler=self._setup_request_handler())
        self.app = a2a_app.build(agent_card_url=self.agent_card_path)

        # add the middleware
        self.app.add_middleware(LoggingMiddleware, logger=self.logger)
        for middleware_info in self._middlewares:
            middleware, kwargs = middleware_info
            self.app.add_middleware(middleware, **kwargs)

        self.logger.info(f"A2A agent set up at {self.agent_card_path}")
        self.logger.info(f"A2A agent listening at {self.path}")

        self.http.app.mount(self.path, self.app)

    def _setup_executor(self) -> AgentExecutor:
        return CustomAgentExecutor(self.emit)

    def _setup_request_handler(self) -> RequestHandler:
        return DefaultRequestHandler(
            agent_executor=self.custom_executor if self.custom_executor else self._setup_executor(),
            task_store=self.task_store,
        )
