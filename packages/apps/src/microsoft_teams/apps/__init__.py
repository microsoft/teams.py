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
from .history import (
    ChannelHistorySource,
    GroupChatHistorySource,
    HistorySource,
    MessageHistory,
    OneOnOneHistorySource,
)
from .http import FastAPIAdapter, HttpServer, HttpServerAdapter
from .http_stream import HttpStream
from .options import AppOptions
from .plugins import *  # noqa: F401, F403
from .routing import ActivityContext
from .utils.thread import get_base_conversation_id, get_thread_message_id, to_threaded_conversation_id

logging.getLogger(__name__).addHandler(logging.NullHandler())

# Combine all exports from submodules
__all__: list[str] = [
    "App",
    "AppOptions",
    "HttpServer",
    "HttpServerAdapter",
    "FastAPIAdapter",
    "ChannelHistorySource",
    "GroupChatHistorySource",
    "HistorySource",
    "HttpStream",
    "MessageHistory",
    "OneOnOneHistorySource",
    "ActivityContext",
    "get_base_conversation_id",
    "get_thread_message_id",
    "to_threaded_conversation_id",
]
__all__.extend(auth.__all__)
__all__.extend(events.__all__)
__all__.extend(plugins.__all__)
__all__.extend(contexts.__all__)
