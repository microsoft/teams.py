"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from unittest.mock import MagicMock, patch

import pytest

from microsoft.teams.api import JsonWebToken
from microsoft.teams.apps.routing.activity_context import _get_graph_client


class TestOptionalGraphDependencies:
    """Test that graph functionality is properly optional."""

    def test_get_graph_client_without_graph_available(self):
        """Test _get_graph_client when graph dependencies are not available."""
        mock_token = JsonWebToken(
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        )

        # Mock import error for graph module
        def mock_import(name, *args, **kwargs):
            if name == "microsoft.teams.graph":
                raise ImportError("No module named 'microsoft.teams.graph'")
            return __import__(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            with pytest.raises(ImportError) as exc_info:
                _get_graph_client(mock_token)

            assert "Graph functionality not available" in str(exc_info.value)
            assert "pip install microsoft-teams-apps[graph]" in str(exc_info.value)

    def test_get_graph_client_with_graph_available(self):
        """Test _get_graph_client when graph dependencies are available."""
        mock_token = JsonWebToken(
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        )

        # Mock successful graph module import and get_graph_client function
        mock_graph_client = MagicMock()
        
        # We need to patch the import itself since get_graph_client is imported inside _get_graph_client
        with patch("builtins.__import__") as mock_import:
            # Create a mock module that has get_graph_client
            mock_graph_module = MagicMock()
            mock_graph_module.get_graph_client.return_value = mock_graph_client
            
            # Set up the import mock to return our mock module for microsoft.teams.graph
            def import_side_effect(name, *args, **kwargs):
                if name == "microsoft.teams.graph":
                    return mock_graph_module
                return __import__(name, *args, **kwargs)
            
            mock_import.side_effect = import_side_effect

            result = _get_graph_client(mock_token)

            assert result is mock_graph_client
            mock_graph_module.get_graph_client.assert_called_once_with(mock_token)
