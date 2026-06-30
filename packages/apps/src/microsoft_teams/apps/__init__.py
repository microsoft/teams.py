"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import logging

from . import auth, contexts, events, plugins
from .app import App
from .auth import *  # noqa: F403
from .contexts import *  # noqa: F403
from .events import *  # noqa: F401, F403
from .http import FastAPIAdapter, HttpServerAdapter
from .http_stream import HttpStream
from .options import AppOptions
from .plugins import *  # noqa: F401, F403
from .routing import ActivityContext
from .utils.html_widget import (
    HtmlWidgetMarkdownOptions,
    InjectWidgetProtocolOptions,
    SecurityPolicyWarning,
    build_html_widget_markdown,
    build_html_widget_message,
    inject_widget_protocol,
    validate_security_policy,
)
from .utils.thread import to_threaded_conversation_id

logging.getLogger(__name__).addHandler(logging.NullHandler())

# Combine all exports from submodules
__all__: list[str] = [
    "App",
    "AppOptions",
    "HttpServerAdapter",
    "FastAPIAdapter",
    "HttpStream",
    "ActivityContext",
    "to_threaded_conversation_id",
    "build_html_widget_markdown",
    "build_html_widget_message",
    "inject_widget_protocol",
    "validate_security_policy",
    "HtmlWidgetMarkdownOptions",
    "InjectWidgetProtocolOptions",
    "SecurityPolicyWarning",
]
__all__.extend(auth.__all__)
__all__.extend(events.__all__)
__all__.extend(plugins.__all__)
__all__.extend(contexts.__all__)
