"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import List, Optional

from microsoft.teams.common.http import Client, ClientOptions

from ...models import Account


class ConversationMemberClient:
    """
    Client for managing members in a Teams conversation.
    """

    def __init__(self, service_url: str, http_client: Optional[Client] = None):
        """
        Initialize the conversation member client.

        Args:
            service_url: The base URL for the Teams service
            http_client: Optional HTTP client to use. If not provided, a new one will be created.
        """
        self.service_url = service_url
        self._http = http_client or Client(ClientOptions())

    @property
    def http(self) -> Client:
        """Get the HTTP client."""
        return self._http

    @http.setter
    def http(self, client: Client) -> None:
        """Set the HTTP client."""
        self._http = client

    async def get(self, conversation_id: str) -> List[Account]:
        """
        Get all members in a conversation.

        Args:
            conversation_id: The ID of the conversation

        Returns:
            List of Account objects representing the conversation members
        """
        response = await self._http.get(f"{self.service_url}/v3/conversations/{conversation_id}/members")
        return [Account.model_validate(member) for member in response.json()]

    async def get_by_id(self, conversation_id: str, member_id: str) -> Account:
        """
        Get a specific member in a conversation.

        Args:
            conversation_id: The ID of the conversation
            member_id: The ID of the member to get

        Returns:
            Account object representing the conversation member
        """
        response = await self._http.get(f"{self.service_url}/v3/conversations/{conversation_id}/members/{member_id}")
        return Account.model_validate(response.json())

    async def delete(self, conversation_id: str, member_id: str) -> None:
        """
        Remove a member from a conversation.

        Args:
            conversation_id: The ID of the conversation
            member_id: The ID of the member to remove
        """
        await self._http.delete(f"{self.service_url}/v3/conversations/{conversation_id}/members/{member_id}")
