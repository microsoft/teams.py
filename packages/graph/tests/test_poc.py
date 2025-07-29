"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.

Basic POC tests to validate the Graph integration approach.
"""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from microsoft.teams.graph.auth_provider import TeamsContextAuthProvider
from microsoft.teams.graph.context_extension import GraphIntegrationError, enable_graph_integration


class TestAuthProvider:
    """Test the Teams to Graph authentication bridge."""

    def test_auth_provider_with_valid_token(self):
        """Test that auth provider can extract token from context."""
        # Mock Teams SDK context
        mock_context = Mock()
        mock_context.is_signed_in = True

        # Mock user token
        mock_token = Mock()
        mock_token.__str__ = Mock(return_value="fake-token-123")
        mock_token.token.valid_to = datetime.utcnow() + timedelta(hours=1)
        mock_context.user_graph_token = mock_token

        # Test auth provider
        auth_provider = TeamsContextAuthProvider(mock_context)
        access_token = auth_provider.get_token()

        assert access_token.token == "fake-token-123"
        assert access_token.expires_on == mock_token.token.valid_to

    def test_auth_provider_no_token(self):
        """Test that auth provider raises error when no token available."""
        mock_context = Mock()
        mock_context.user_graph_token = None

        auth_provider = TeamsContextAuthProvider(mock_context)

        with pytest.raises(ValueError, match="User must be signed in"):
            auth_provider.get_token()

    def test_token_caching(self):
        """Test that tokens are cached and reused when valid."""
        mock_context = Mock()
        mock_token = Mock()
        mock_token.__str__ = Mock(return_value="cached-token")
        mock_token.token.valid_to = datetime.utcnow() + timedelta(hours=1)
        mock_context.user_graph_token = mock_token

        auth_provider = TeamsContextAuthProvider(mock_context)

        # First call should get token from context
        token1 = auth_provider.get_token()

        # Second call should use cached token (context won't be called again)
        mock_context.user_graph_token = None  # Simulate context being unavailable
        token2 = auth_provider.get_token()

        assert token1.token == token2.token == "cached-token"

    def test_token_expiry_buffer(self):
        """Test that tokens are refreshed before they expire."""
        mock_context = Mock()

        # Create token that expires in 3 minutes (within 5-minute buffer)
        mock_token = Mock()
        mock_token.__str__ = Mock(return_value="expiring-token")
        mock_token.token.valid_to = datetime.utcnow() + timedelta(minutes=3)
        mock_context.user_graph_token = mock_token

        auth_provider = TeamsContextAuthProvider(mock_context)

        # First call should cache the token
        auth_provider.get_token()

        # Create a new token for refresh
        new_token = Mock()
        new_token.__str__ = Mock(return_value="refreshed-token")
        new_token.token.valid_to = datetime.utcnow() + timedelta(hours=1)
        mock_context.user_graph_token = new_token

        # Second call should refresh token due to expiry buffer
        token = auth_provider.get_token()
        assert token.token == "refreshed-token"


class TestContextExtension:
    """Test the ActivityContext integration."""

    @patch("microsoft.teams.graph.context_extension.GraphServiceClient")
    def test_context_extension_integration(self, mock_graph_client):
        """Test that context extension can be added and accessed."""
        # Enable the integration
        enable_graph_integration()

        # Verify the property was added
        from microsoft.teams.app.routing import ActivityContext

        assert hasattr(ActivityContext, "graph")

        # Create mock context
        mock_context = Mock(spec=ActivityContext)
        mock_context.is_signed_in = True

        # Mock user token
        mock_token = Mock()
        mock_token.__str__ = Mock(return_value="test-token")
        mock_token.token.valid_to = datetime.utcnow() + timedelta(hours=1)
        mock_context.user_graph_token = mock_token

        # Access the graph property - should create GraphServiceClient
        # We need to bind the property to our mock context
        graph_property = ActivityContext.graph
        result = graph_property.fget(mock_context)

        # Verify GraphServiceClient was created
        mock_graph_client.assert_called_once()
        assert result == mock_graph_client.return_value

    def test_context_extension_not_signed_in(self):
        """Test that accessing graph property raises error when not signed in."""
        enable_graph_integration()

        from microsoft.teams.app.routing import ActivityContext

        # Create mock context that's not signed in
        mock_context = Mock(spec=ActivityContext)
        mock_context.is_signed_in = False

        # Access the graph property - should raise error
        graph_property = ActivityContext.graph

        with pytest.raises(GraphIntegrationError, match="User must be signed in"):
            graph_property.fget(mock_context)


class TestPOCIntegration:
    """End-to-end POC tests."""

    @patch("microsoft.teams.graph.context_extension.GraphServiceClient")
    def test_full_integration_flow(self, mock_graph_client):
        """Test the complete integration flow."""
        # Enable Graph integration
        enable_graph_integration()

        # Create mock Teams context
        from microsoft.teams.app.routing import ActivityContext

        mock_context = Mock(spec=ActivityContext)
        mock_context.is_signed_in = True

        # Mock user token
        mock_token = Mock()
        mock_token.__str__ = Mock(return_value="integration-token")
        mock_token.token.valid_to = datetime.utcnow() + timedelta(hours=1)
        mock_context.user_graph_token = mock_token

        # Mock Graph client and me.get() response
        mock_me_client = Mock()
        mock_me_response = Mock()
        mock_me_response.display_name = "Test User"
        mock_me_client.get = Mock(return_value=mock_me_response)

        mock_graph_instance = Mock()
        mock_graph_instance.me = mock_me_client
        mock_graph_client.return_value = mock_graph_instance

        # Test the integration
        graph_property = ActivityContext.graph
        graph_client = graph_property.fget(mock_context)

        # Verify we got the mocked Graph client
        assert graph_client == mock_graph_instance

        # Verify the auth provider was created with correct parameters
        mock_graph_client.assert_called_once()
        call_args = mock_graph_client.call_args

        # Check that credentials parameter is our auth provider
        credentials = call_args.kwargs["credentials"]
        assert isinstance(credentials, TeamsContextAuthProvider)

        # Check that scopes are set correctly
        assert call_args.kwargs["scopes"] == ["https://graph.microsoft.com/.default"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
