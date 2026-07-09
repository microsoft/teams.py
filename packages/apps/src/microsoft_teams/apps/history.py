"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from importlib import import_module
from typing import TYPE_CHECKING, Annotated, Any, Literal, cast

from microsoft_teams.api import CustomBaseModel
from pydantic import Field

_GRAPH_PAGE_SIZE_LIMIT = 50
_CHAT_HISTORY_ORDER_BY = ["createdDateTime desc"]

if TYPE_CHECKING:
    from msgraph.generated.models.chat_message import ChatMessage  # type: ignore[reportMissingTypeStubs]
    from msgraph.graph_service_client import GraphServiceClient
else:
    ChatMessage = Any


class OneOnOneHistorySource(CustomBaseModel):
    """Message history source for a 1:1 chat."""

    type: Literal["oneOnOne"] = "oneOnOne"
    chat_id: str


class GroupChatHistorySource(CustomBaseModel):
    """Message history source for a group chat."""

    type: Literal["groupChat"] = "groupChat"
    chat_id: str


class ChannelHistorySource(CustomBaseModel):
    """Message history source for a Teams channel or channel thread."""

    type: Literal["channel"] = "channel"
    team_aad_group_id: str
    channel_id: str
    thread_id: str | None = None


HistorySource = Annotated[
    OneOnOneHistorySource | GroupChatHistorySource | ChannelHistorySource,
    Field(discriminator="type"),
]


class MessageHistory(CustomBaseModel):
    """Messages returned from Graph plus the source used to retrieve them."""

    messages: list[ChatMessage]
    source: HistorySource


def _validate_history_count(n: object) -> None:
    if type(n) is not int:
        raise TypeError("n must be an integer")
    if n < 1:
        raise ValueError("n must be greater than 0")


def _get_query_parameters(messages_builder: Any, n: int, *, orderby: list[str] | None = None) -> Any:
    builder_type = cast(type[Any], type(messages_builder))
    for name in ("MessagesRequestBuilderGetQueryParameters", "RepliesRequestBuilderGetQueryParameters"):
        query_parameters_type = getattr(builder_type, name, None)
        if query_parameters_type is not None:
            return query_parameters_type(top=n, orderby=orderby)

    raise TypeError("messages_builder does not support Graph history query parameters")


def _get_request_configuration(messages_builder: Any, n: int, *, orderby: list[str] | None = None) -> Any:
    try:
        from kiota_abstractions.base_request_configuration import RequestConfiguration
    except ImportError as e:
        raise ImportError(
            "Graph functionality not available. Install with 'pip install microsoft-teams-apps[graph]'"
        ) from e

    return RequestConfiguration(query_parameters=_get_query_parameters(messages_builder, n, orderby=orderby))


def _get_error_mapping() -> dict[str, Any]:
    ODataError = import_module("msgraph.generated.models.o_data_errors.o_data_error").ODataError
    return {"4XX": ODataError, "5XX": ODataError}


def _last_n_messages(messages: list[Any], n: int) -> list[Any]:
    if all(getattr(message, "created_date_time", None) is not None for message in messages):
        messages = sorted(messages, key=lambda message: message.created_date_time)
    return messages[-n:]


async def get_graph_history(
    graph: "GraphServiceClient",
    n: int,
    *,
    source: HistorySource,
) -> MessageHistory:
    """
    Retrieve Teams message history with Microsoft Graph.

    The provided ``source`` selects either ``/chats/{chat-id}/messages`` or
    ``/teams/{team-aad-group-id}/channels/{channel-id}/messages``. When a
    channel source includes ``thread_id``, replies for that root message are
    returned.
    """
    _validate_history_count(n)

    if isinstance(source, ChannelHistorySource):
        team_builder = graph.teams.by_team_id(source.team_aad_group_id)
        channel_builder = team_builder.channels.by_channel_id(source.channel_id)
        messages_builder = channel_builder.messages
        if source.thread_id:
            messages_builder = messages_builder.by_chat_message_id(source.thread_id).replies
        orderby = None
    else:
        messages_builder = graph.chats.by_chat_id(source.chat_id).messages
        orderby = _CHAT_HISTORY_ORDER_BY

    messages: list[ChatMessage] = []
    collect_all = isinstance(source, ChannelHistorySource) and source.thread_id is not None
    page_size = _GRAPH_PAGE_SIZE_LIMIT if collect_all else min(n, _GRAPH_PAGE_SIZE_LIMIT)
    response = await messages_builder.get(_get_request_configuration(messages_builder, page_size, orderby=orderby))
    if response is None or response.value is None:
        return MessageHistory(messages=[], source=source)

    try:
        from msgraph_core.tasks.page_iterator import PageIterator  # type: ignore[reportMissingTypeStubs]
    except ImportError as e:
        raise ImportError(
            "Graph functionality not available. Install with 'pip install microsoft-teams-apps[graph]'"
        ) from e

    def collect(message: ChatMessage) -> bool:
        messages.append(message)
        return collect_all or len(messages) < n

    request_adapter: Any = graph.request_adapter  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
    iterator: Any = PageIterator(response, request_adapter, error_mapping=_get_error_mapping())
    await iterator.iterate(collect)
    if collect_all:
        messages = _last_n_messages(messages, n)
    return MessageHistory(messages=messages, source=source)
