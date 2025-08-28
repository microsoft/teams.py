"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

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
            # app_graph should return None when graph dependencies are not available
            result = activity_context.app_graph
            assert result is None

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
