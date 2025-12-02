"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

import pytest
from microsoft.teams.api.models import TeamsChannelAccount


@pytest.mark.unit
class TestTeamsChannelAccount:
    """Unit tests for TeamsChannelAccount."""

    def test_teams_channel_account_creation_minimal(self):
        """Test creating TeamsChannelAccount with minimal required fields."""
        account = TeamsChannelAccount(id="user-123")

        assert account.id == "user-123"
        assert account.name is None
        assert account.object_id is None
        assert account.role is None
        assert account.given_name is None
        assert account.surname is None
        assert account.email is None
        assert account.user_principal_name is None
        assert account.tenant_id is None
        assert account.properties is None

    def test_teams_channel_account_creation_full(self):
        """Test creating TeamsChannelAccount with all fields."""
        account = TeamsChannelAccount(
            id="user-123",
            name="John Doe",
            object_id="aad-object-id-456",
            role="user",
            given_name="John",
            surname="Doe",
            email="john.doe@example.com",
            user_principal_name="john.doe@contoso.onmicrosoft.com",
            tenant_id="tenant-789",
            properties={"custom_key": "custom_value"},
        )

        assert account.id == "user-123"
        assert account.name == "John Doe"
        assert account.object_id == "aad-object-id-456"
        assert account.role == "user"
        assert account.given_name == "John"
        assert account.surname == "Doe"
        assert account.email == "john.doe@example.com"
        assert account.user_principal_name == "john.doe@contoso.onmicrosoft.com"
        assert account.tenant_id == "tenant-789"
        assert account.properties == {"custom_key": "custom_value"}

    def test_teams_channel_account_bot_role(self):
        """Test TeamsChannelAccount with bot role."""
        account = TeamsChannelAccount(
            id="bot-123",
            name="Test Bot",
            role="bot",
        )

        assert account.id == "bot-123"
        assert account.name == "Test Bot"
        assert account.role == "bot"

    def test_teams_channel_account_serialization(self):
        """Test TeamsChannelAccount model_dump serialization."""
        account = TeamsChannelAccount(
            id="user-123",
            name="John Doe",
            given_name="John",
            surname="Doe",
            email="john.doe@example.com",
        )

        data = account.model_dump(exclude_none=True)

        assert data["id"] == "user-123"
        assert data["name"] == "John Doe"
        # Serialization uses camelCase aliases
        assert data["givenName"] == "John"
        assert data["surname"] == "Doe"
        assert data["email"] == "john.doe@example.com"
        assert "objectId" not in data
        assert "role" not in data

    def test_teams_channel_account_validation(self):
        """Test TeamsChannelAccount model validation from dict."""
        data = {
            "id": "user-456",
            "name": "Jane Smith",
            "objectId": "aad-789",
            "givenName": "Jane",
            "surname": "Smith",
            "email": "jane.smith@example.com",
            "userPrincipalName": "jane.smith@contoso.onmicrosoft.com",
            "tenantId": "tenant-abc",
        }

        account = TeamsChannelAccount.model_validate(data)

        assert account.id == "user-456"
        assert account.name == "Jane Smith"
        assert account.object_id == "aad-789"
        assert account.given_name == "Jane"
        assert account.surname == "Smith"
        assert account.email == "jane.smith@example.com"
        assert account.user_principal_name == "jane.smith@contoso.onmicrosoft.com"
        assert account.tenant_id == "tenant-abc"

    def test_teams_channel_account_with_extra_properties(self):
        """Test TeamsChannelAccount handles extra properties gracefully."""
        data = {
            "id": "user-123",
            "name": "Test User",
            "unknownField": "should be ignored",
        }

        # Should not raise an error with extra fields
        account = TeamsChannelAccount.model_validate(data)
        assert account.id == "user-123"
        assert account.name == "Test User"
