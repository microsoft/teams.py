"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from microsoft_teams.apps.routing.activity_context import ActivityContext


class TestOptionalGraphDependencies:
    """Test that graph functionality is properly optional."""

    def _create_activity_context(self) -> ActivityContext[Any]:
        """Create a minimal ActivityContext for testing."""
        # Create mock objects for all required parameters
        mock_activity = MagicMock()
        mock_storage = MagicMock()
        mock_api = MagicMock()
        mock_conversation_ref = MagicMock()
        mock_activity_sender = MagicMock()
        mock_activity_sender.create_stream.return_value = MagicMock()
        mock_app_token = MagicMock()  # Provide an app token for graph access

        return ActivityContext(
            activity=mock_activity,
            app_id="test-app-id",
            storage=mock_storage,
            api=mock_api,
            user_token=None,
            conversation_ref=mock_conversation_ref,
            is_signed_in=False,
            connection_name="test-connection",
            activity_sender=mock_activity_sender,
            app_token=mock_app_token,  # This is needed for app_graph to work
        )

    def test_app_graph_property_without_graph_available(self) -> None:
        """Test app_graph property when graph dependencies are not available."""

        # Mock import error for graph module
        def mock_import(name: str, *args: Any, **kwargs: Any) -> Any:
            if name == "microsoft_teams.graph":
                raise ImportError("No module named 'microsoft_teams.graph'")
            return __import__(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            activity_context = self._create_activity_context()
            # app_graph should raise RuntimeError when graph dependencies are not available
            with pytest.raises(RuntimeError, match="Failed to create app graph client"):
                _ = activity_context.app_graph

    def test_app_graph_property_with_graph_available(self) -> None:
        """Test app_graph property when graph dependencies are available."""

        # Mock successful graph module import
        def mock_import(name: str, *args: Any, **kwargs: Any) -> Any:
            if name == "microsoft_teams.graph":
                # Create a mock module with get_graph_client
                mock_module = SimpleNamespace()
                mock_module.get_graph_client = lambda x: "MockGraphClient"  # type: ignore
                return mock_module
            return __import__(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            activity_context = self._create_activity_context()
            result = activity_context.app_graph
            assert result == "MockGraphClient"

    def test_user_graph_property_not_signed_in(self) -> None:
        """Test user_graph property when user is not signed in."""
        activity_context = ActivityContext(
            activity=MagicMock(),
            app_id="test-app-id",
            storage=MagicMock(),
            api=MagicMock(),
            user_token=MagicMock(),  # Has token but not signed in
            conversation_ref=MagicMock(),
            is_signed_in=False,  # Not signed in
            connection_name="test-connection",
            activity_sender=MagicMock(),
            app_token=None,
        )

        # user_graph should raise ValueError when user is not signed in
        with pytest.raises(ValueError, match="User must be signed in to access Graph client"):
            _ = activity_context.user_graph

    def test_user_graph_property_no_token(self) -> None:
        """Test user_graph property when user is signed in but has no token."""
        activity_context = ActivityContext(
            activity=MagicMock(),
            app_id="test-app-id",
            storage=MagicMock(),
            api=MagicMock(),
            user_token=None,  # No token
            conversation_ref=MagicMock(),
            is_signed_in=True,  # Signed in but no token
            connection_name="test-connection",
            activity_sender=MagicMock(),
            app_token=None,
        )

        # user_graph should raise ValueError when no user token is available
        with pytest.raises(ValueError, match="No user token available for Graph client"):
            _ = activity_context.user_graph

    def test_app_graph_property_no_token(self) -> None:
        """Test app_graph property when no app token is available."""
        activity_context = ActivityContext(
            activity=MagicMock(),
            app_id="test-app-id",
            storage=MagicMock(),
            api=MagicMock(),
            user_token=None,
            conversation_ref=MagicMock(),
            is_signed_in=False,
            connection_name="test-connection",
            activity_sender=MagicMock(),
            app_token=None,  # No app token
        )

        # app_graph should raise ValueError when no app token is available
        with pytest.raises(RuntimeError, match="Token cannot be None"):
            _ = activity_context.app_graph


class TestAppGetAppGraph:
    """Test App.get_app_graph method."""

    def _create_app(self):
        from microsoft_teams.apps import App, AppOptions

        return App(**AppOptions(client_id="test-id", client_secret="test-secret"))

    def test_get_app_graph_raises_import_error_when_graph_not_installed(self) -> None:
        """get_app_graph raises ImportError when graph dependencies are not available."""
        app = self._create_app()

        with patch(
            "microsoft_teams.apps.app._get_graph_client",
            side_effect=ImportError("graph not installed"),
        ):
            with pytest.raises(ImportError):
                _ = app.get_app_graph()

    def test_get_app_graph_returns_new_client_each_call(self) -> None:
        """get_app_graph returns a new client on every call (no caching)."""
        app = self._create_app()

        mock_client_1 = MagicMock()
        mock_client_2 = MagicMock()
        side_effects = [mock_client_1, mock_client_2]

        with patch(
            "microsoft_teams.apps.app._get_graph_client",
            side_effect=side_effects,
        ):
            first = app.get_app_graph()
            second = app.get_app_graph()

        assert first is mock_client_1
        assert second is mock_client_2
        assert first is not second

    def test_get_app_graph_passes_tenant_id(self) -> None:
        """get_app_graph passes the tenant_id through to the token factory."""
        app = self._create_app()

        mock_client = MagicMock()
        captured_token_arg = []

        def capture_token(token):
            captured_token_arg.append(token)
            return mock_client

        with patch(
            "microsoft_teams.apps.app._get_graph_client",
            side_effect=capture_token,
        ):
            app.get_app_graph(tenant_id="my-tenant-id")

        assert len(captured_token_arg) == 1
        # token arg should be a callable (lambda)
        assert callable(captured_token_arg[0])
