"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional, Union

from microsoft_teams.common.http import Client, ClientOptions

from ...models.batch import BatchOperationResult
from ..api_client_settings import ApiClientSettings
from ..base_client import BaseClient
from .params import BatchChannelsParams, BatchTeamParams, BatchTenantParams, BatchUsersParams


class BatchClient(BaseClient):
    """Client for sending messages to large audiences in batch."""

    def __init__(
        self,
        service_url: str,
        options: Optional[Union[Client, ClientOptions]] = None,
        api_client_settings: Optional[ApiClientSettings] = None,
    ) -> None:
        super().__init__(options, api_client_settings)
        self.service_url = service_url.rstrip("/")

    async def send_to_users(self, params: BatchUsersParams) -> BatchOperationResult:
        """
        Send a message to a specific list of users.

        Args:
            params: The batch users parameters including tenant_id, members, and activity.

        Returns:
            BatchOperationResult containing the operation_id to track the operation.
        """
        response = await self.http.post(
            f"{self.service_url}/v3/batch/conversation/users",
            json=params.model_dump(by_alias=True, exclude_none=True),
        )
        return BatchOperationResult.model_validate(response.json())

    async def send_to_tenant(self, params: BatchTenantParams) -> BatchOperationResult:
        """
        Send a message to all users in a tenant.

        Args:
            params: The batch tenant parameters including tenant_id and activity.

        Returns:
            BatchOperationResult containing the operation_id to track the operation.
        """
        response = await self.http.post(
            f"{self.service_url}/v3/batch/conversation/tenant",
            json=params.model_dump(by_alias=True, exclude_none=True),
        )
        return BatchOperationResult.model_validate(response.json())

    async def send_to_team(self, params: BatchTeamParams) -> BatchOperationResult:
        """
        Send a message to all members of a team.

        Args:
            params: The batch team parameters including tenant_id, team_id, and activity.

        Returns:
            BatchOperationResult containing the operation_id to track the operation.
        """
        response = await self.http.post(
            f"{self.service_url}/v3/batch/conversation/team",
            json=params.model_dump(by_alias=True, exclude_none=True),
        )
        return BatchOperationResult.model_validate(response.json())

    async def send_to_channels(self, params: BatchChannelsParams) -> BatchOperationResult:
        """
        Send a message to a list of channels.

        Args:
            params: The batch channels parameters including tenant_id, members, and activity.

        Returns:
            BatchOperationResult containing the operation_id to track the operation.
        """
        response = await self.http.post(
            f"{self.service_url}/v3/batch/conversation/channels",
            json=params.model_dump(by_alias=True, exclude_none=True),
        )
        return BatchOperationResult.model_validate(response.json())
