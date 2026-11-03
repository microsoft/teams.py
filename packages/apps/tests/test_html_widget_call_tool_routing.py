"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

import warnings
from unittest.mock import MagicMock

from microsoft_teams.api import ActivityTypeAdapter, HtmlWidgetCallToolInvokeActivity
from microsoft_teams.apps import App
from microsoft_teams.common.experimental import ExperimentalWarning

warnings.filterwarnings("ignore", category=ExperimentalWarning)

ARGUMENTS = {
    "counter": 3,
    "nested": {"a": [1, 2, {"b": None}]},
    "__msteams__": {"mcpUrl": "contoso.example", "correlationId": "cv123.0", "extra": True},
}


def _payload(arguments):
    return {
        "type": "invoke",
        "id": "act-1",
        "name": "htmlwidget/calltool",
        "channelId": "msteams",
        "from": {"id": "user-1", "name": "User"},
        "recipient": {"id": "bot-1", "name": "Bot"},
        "conversation": {"id": "conv-1", "conversationType": "personal"},
        "value": {"name": "refresh", "arguments": arguments},
    }


def _app() -> App:
    return App(storage=MagicMock(), client_id="test-client-id", client_secret="test-secret")


class TestWidgetCallToolRouting:
    def test_activity_keeps_arguments_untouched(self):
        activity = ActivityTypeAdapter.validate_python(_payload(ARGUMENTS))
        assert isinstance(activity, HtmlWidgetCallToolInvokeActivity)
        assert activity.value.name == "refresh"
        assert activity.value.arguments == ARGUMENTS

    def test_route_selects_handler(self):
        app = _app()

        @app.on_widget_call_tool
        async def handler(ctx):
            return None

        activity = ActivityTypeAdapter.validate_python(_payload(ARGUMENTS))
        assert app.router.select_handlers(activity) == [handler]

    async def test_handler_receives_arguments_including_msteams(self):
        app = _app()
        received = {}

        @app.on_widget_call_tool
        async def handler(ctx):
            received["arguments"] = ctx.activity.value.arguments
            return None

        activity = ActivityTypeAdapter.validate_python(_payload(ARGUMENTS))
        (selected,) = app.router.select_handlers(activity)
        ctx = MagicMock()
        ctx.activity = activity
        await selected(ctx)

        assert received["arguments"] == ARGUMENTS
        assert received["arguments"]["__msteams__"] == ARGUMENTS["__msteams__"]

    def test_missing_arguments_stay_none(self):
        activity = ActivityTypeAdapter.validate_python(_payload(None))
        assert activity.value.arguments is None
