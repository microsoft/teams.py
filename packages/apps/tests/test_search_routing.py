"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

from unittest.mock import MagicMock

import pytest
from microsoft_teams.api import (
    Account,
    AdaptiveCardInvokeActivity,
    ConversationAccount,
    SearchInvokeActivity,
    SearchInvokeResponse,
)
from microsoft_teams.api.models.adaptive_card import AdaptiveCardInvokeAction, AdaptiveCardInvokeValue
from microsoft_teams.api.models.search import (
    SearchInvokeResponseValue,
    SearchInvokeResult,
    SearchInvokeValue,
    SearchResponse,
)
from microsoft_teams.apps import ActivityContext, App

FROM_ACCOUNT = Account(id="user-123", name="Test User")
RECIPIENT = Account(id="bot-456", name="Test Bot")
CONVERSATION = ConversationAccount(id="conv-789", conversation_type="personal")


class TestSearchRouting:
    """Test cases for application/search (dynamic typeahead) routing."""

    @pytest.fixture
    def mock_storage(self):
        return MagicMock()

    @pytest.fixture(scope="function")
    def app_with_options(self, mock_storage):
        return App(storage=mock_storage, client_id="test-client-id", client_secret="test-secret")

    def _search_activity(self) -> SearchInvokeActivity:
        return SearchInvokeActivity(
            id="test-activity-id",
            type="invoke",
            name="application/search",
            from_=FROM_ACCOUNT,
            recipient=RECIPIENT,
            conversation=CONVERSATION,
            channel_id="msteams",
            value=SearchInvokeValue(kind="search", query_text="hello", dataset="cities"),
        )

    def test_on_card_search_matches_application_search(self, app_with_options: App) -> None:
        """on_card_search should match an application/search invoke."""

        @app_with_options.on_card_search
        async def handle_search(ctx: ActivityContext[SearchInvokeActivity]) -> SearchInvokeResponse:
            return SearchResponse(
                value=SearchInvokeResponseValue(results=[SearchInvokeResult(title="Example", value="example")])
            )

        handlers = app_with_options.router.select_handlers(self._search_activity())
        assert len(handlers) == 1
        assert handlers[0] == handle_search

    def test_on_card_search_does_not_match_other_invokes(self, app_with_options: App) -> None:
        """on_card_search should not match a different invoke name."""

        @app_with_options.on_card_search
        async def handle_search(ctx: ActivityContext[SearchInvokeActivity]) -> SearchInvokeResponse:
            return SearchResponse(value=SearchInvokeResponseValue(results=[]))

        card_activity = AdaptiveCardInvokeActivity(
            id="test-activity-id-2",
            type="invoke",
            name="adaptiveCard/action",
            from_=FROM_ACCOUNT,
            recipient=RECIPIENT,
            conversation=CONVERSATION,
            channel_id="msteams",
            value=AdaptiveCardInvokeValue(
                action=AdaptiveCardInvokeAction(type="Action.Execute", data={"action": "submit"})
            ),
        )

        assert len(app_with_options.router.select_handlers(card_activity)) == 0

    def test_search_value_deserializes_camel_case(self) -> None:
        """SearchInvokeValue should accept camelCase JSON from the Teams client."""
        value = SearchInvokeValue.model_validate(
            {"kind": "typeahead", "queryText": "sea", "queryOptions": {"skip": 0, "top": 5}, "dataset": "cities"}
        )
        assert value.query_text == "sea"
        assert value.query_options is not None
        assert value.query_options.top == 5

    def test_search_value_deserializes_without_kind(self) -> None:
        """Adaptive Card dynamic typeahead omits 'kind'; SearchInvokeValue must still validate."""
        value = SearchInvokeValue.model_validate(
            {"queryText": "mario", "queryOptions": {"skip": 0, "top": 5}, "dataset": "nintendoGames"}
        )
        assert value.kind is None
        assert value.query_text == "mario"
        assert value.dataset == "nintendoGames"

    def test_search_response_serializes_camel_case(self) -> None:
        """SearchResponse should serialize to the documented camelCase shape."""
        response = SearchResponse(
            value=SearchInvokeResponseValue(results=[SearchInvokeResult(title="Seattle", value="seattle")])
        )
        dumped = response.model_dump(by_alias=True)
        assert dumped["statusCode"] == 200
        assert dumped["type"] == "application/vnd.microsoft.search.searchResponse"
        assert dumped["value"]["results"][0]["title"] == "Seattle"
