"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from microsoft.teams.apps.routing.activity_context import ActivityContext


class TestOptionalGraphDependencies:
    """Test that graph functionality is properly optional."""

    def _create_activity_context(self) -> ActivityContext[Any]:
        """Create a minimal ActivityContext for testing."""
        # Create mock objects for all required parameters
        mock_activity = MagicMock()
        mock_logger = MagicMock()
        mock_storage = MagicMock()
        mock_api = MagicMock()
        mock_conversation_ref = MagicMock()
        mock_sender = MagicMock()
        mock_app_token = MagicMock()  # Provide an app token for graph access

        return ActivityContext(
            activity=mock_activity,
            app_id="test-app-id",
            logger=mock_logger,
            storage=mock_storage,
            api=mock_api,
            user_token=None,
            conversation_ref=mock_conversation_ref,
            is_signed_in=False,
            connection_name="test-connection",
            sender=mock_sender,
            app_token=mock_app_token,  # This is needed for app_graph to work
        )

    def test_app_graph_property_without_graph_available(self) -> None:
        """Test app_graph property when graph dependencies are not available."""

        # Mock import error for graph module
        def mock_import(name: str, *args: Any, **kwargs: Any) -> Any:
            if name == "microsoft.teams.graph":
                raise ImportError("No module named 'microsoft.teams.graph'")
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
            if name == "microsoft.teams.graph":
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
            logger=MagicMock(),
            storage=MagicMock(),
            api=MagicMock(),
            user_token=MagicMock(),  # Has token but not signed in
            conversation_ref=MagicMock(),
            is_signed_in=False,  # Not signed in
            connection_name="test-connection",
            sender=MagicMock(),
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
            logger=MagicMock(),
            storage=MagicMock(),
            api=MagicMock(),
            user_token=None,  # No token
            conversation_ref=MagicMock(),
            is_signed_in=True,  # Signed in but no token
            connection_name="test-connection",
            sender=MagicMock(),
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
            logger=MagicMock(),
            storage=MagicMock(),
            api=MagicMock(),
            user_token=None,
            conversation_ref=MagicMock(),
            is_signed_in=False,
            connection_name="test-connection",
            sender=MagicMock(),
            app_token=None,  # No app token
        )

        # app_graph should raise ValueError when no app token is available
        with pytest.raises(ValueError, match="No app token available for Graph client"):
            _ = activity_context.app_graph
