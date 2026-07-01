"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from importlib import import_module
from typing import TYPE_CHECKING, Any, List, Optional, Protocol, cast

_GRAPH_PAGE_SIZE_LIMIT = 50

if TYPE_CHECKING:
    from msgraph.generated.models.chat_message import ChatMessage  # type: ignore[reportMissingTypeStubs]
    from msgraph.graph_service_client import GraphServiceClient
else:
    ChatMessage = Any


class _NextPageRequestAdapter(Protocol):
    async def send_async(self, request_info: Any, parsable_factory: Any, error_map: dict[str, Any]) -> Any: ...


def _validate_history_count(n: object) -> None:
    if type(n) is not int:
        raise TypeError("n must be an integer")
    if n < 1:
        raise ValueError("n must be greater than 0")


def _get_query_parameters(messages_builder: Any, n: int) -> Any:
    builder_type = cast(type[Any], type(messages_builder))
    for name in ("MessagesRequestBuilderGetQueryParameters", "RepliesRequestBuilderGetQueryParameters"):
        query_parameters_type = getattr(builder_type, name, None)
        if query_parameters_type is not None:
            return query_parameters_type(top=n)

    raise TypeError("messages_builder does not support Graph history query parameters")


def _get_request_configuration(messages_builder: Any, n: int) -> Any:
    try:
        from kiota_abstractions.base_request_configuration import RequestConfiguration
    except ImportError as e:
        raise ImportError(
            "Graph functionality not available. Install with 'pip install microsoft-teams-apps[graph]'"
        ) from e

    return RequestConfiguration(query_parameters=_get_query_parameters(messages_builder, n))


async def get_graph_history(
    graph: "GraphServiceClient",
    n: int,
    *,
    chat_id: Optional[str] = None,
    channel_id: Optional[str] = None,
    thread_id: Optional[str] = None,
    team_aad_group_id: Optional[str] = None,
) -> List[ChatMessage]:
    """
    Retrieve Teams message history with Microsoft Graph.

    Provide either ``chat_id`` for ``/chats/{chat-id}/messages`` or both
    ``team_aad_group_id`` and ``channel_id`` for
    ``/teams/{team-aad-group-id}/channels/{channel-id}/messages``. When
    ``thread_id`` is supplied, replies for that root message are returned.
    """
    _validate_history_count(n)

    has_chat = bool(chat_id)
    has_channel = bool(team_aad_group_id or channel_id)

    if has_chat == has_channel:
        raise ValueError("provide either chat_id or both team_aad_group_id and channel_id")

    if has_channel:
        if not team_aad_group_id or not channel_id:
            raise ValueError("team_aad_group_id and channel_id are required for channel history")
        messages_builder = graph.teams.by_team_id(team_aad_group_id).channels.by_channel_id(channel_id).messages
    else:
        if not chat_id:
            raise ValueError("chat_id is required for chat history")
        messages_builder = graph.chats.by_chat_id(chat_id).messages

    if thread_id:
        messages_builder = messages_builder.by_chat_message_id(thread_id).replies

    messages: list[ChatMessage] = []
    response = await messages_builder.get(_get_request_configuration(messages_builder, min(n, _GRAPH_PAGE_SIZE_LIMIT)))

    while response is not None:
        if response.value:
            messages.extend(response.value[: n - len(messages)])

        if len(messages) >= n:
            break

        next_link = getattr(response, "odata_next_link", None)
        if not next_link:
            break

        response = await _get_next_page(
            graph.request_adapter,  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
            next_link,
        )

    return messages


async def _get_next_page(request_adapter: _NextPageRequestAdapter, next_link: str) -> Any:
    try:
        from kiota_abstractions.method import Method
        from kiota_abstractions.request_information import RequestInformation
        from msgraph.generated.models.chat_message_collection_response import (  # type: ignore[reportMissingTypeStubs]
            ChatMessageCollectionResponse,
        )
    except ImportError as e:
        raise ImportError(
            "Graph functionality not available. Install with 'pip install microsoft-teams-apps[graph]'"
        ) from e

    ODataError = import_module("msgraph.generated.models.o_data_errors.o_data_error").ODataError
    request_info = RequestInformation(method=Method.GET)
    request_info.path_parameters[RequestInformation.RAW_URL_KEY] = next_link
    return await request_adapter.send_async(
        request_info,
        ChatMessageCollectionResponse,
        {"4XX": ODataError, "5XX": ODataError},
    )
