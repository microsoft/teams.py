"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import logging

from . import auth, contexts, diagnostics, events, files, plugins
from .app import App
from .auth import *  # noqa: F403
from .contexts import *  # noqa: F403
from .diagnostics import *  # noqa: F403
from .events import *  # noqa: F401, F403
from .files import *  # noqa: F403
from .http import FastAPIAdapter, HttpServer, HttpServerAdapter
from .http_stream import HttpStream
from .oauth_flow import OAuthFlow, OAuthFlowRegistry
from .options import AppOptions, AppTelemetryOptions
from .plugins import *  # noqa: F401, F403
from .routing import ActivityContext
from .state import StateOptions, TurnState, TurnStateContainer, TurnStateSealedError, create_state_loader
from .token_provider import AppTokenProvider
from .utils.html_widget import (
    DisplayMode,
    HtmlWidgetMarkdownOptions,
    InjectWidgetProtocolOptions,
    SecurityPolicyWarning,
    WidgetNotification,
    build_html_widget_markdown,
    build_html_widget_message,
    inject_widget_protocol,
    try_get_widget_model_context,
    validate_security_policy,
)
from .utils.thread import to_threaded_conversation_id

logging.getLogger(__name__).addHandler(logging.NullHandler())

# Combine all exports from submodules
__all__: list[str] = [
    "App",
    "AppOptions",
    "AppTelemetryOptions",
    "HttpServer",
    "HttpServerAdapter",
    "FastAPIAdapter",
    "HttpStream",
    "ActivityContext",
    "AppTokenProvider",
    "OAuthFlow",
    "OAuthFlowRegistry",
    "StateOptions",
    "TurnState",
    "TurnStateContainer",
    "TurnStateSealedError",
    "create_state_loader",
    "to_threaded_conversation_id",
    "build_html_widget_markdown",
    "build_html_widget_message",
    "inject_widget_protocol",
    "try_get_widget_model_context",
    "validate_security_policy",
    "HtmlWidgetMarkdownOptions",
    "InjectWidgetProtocolOptions",
    "SecurityPolicyWarning",
    "WidgetNotification",
    "DisplayMode",
]
__all__.extend(auth.__all__)
__all__.extend(diagnostics.__all__)
__all__.extend(events.__all__)
__all__.extend(files.__all__)
__all__.extend(plugins.__all__)
__all__.extend(contexts.__all__)
