"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import List, Optional

from ..custom_base_model import CustomBaseModel
from .messaging_extension_parameter import MessagingExtensionParameter


class MessagingExtensionQueryOptions(CustomBaseModel):
    """
    Messaging extension query options
    """

    skip: Optional[int] = None
    "Number of entities to skip"
    count: Optional[int] = None
    "Number of entities to fetch"


class MessagingExtensionQuery(CustomBaseModel):
    """
    Messaging extension query
    """

    command_id: Optional[str] = None
    "Id of the command assigned by Bot"

    parameters: Optional[List[MessagingExtensionParameter]] = None
    "Parameters for the query"

    query_options: Optional[MessagingExtensionQueryOptions] = None
    "Query options"

    state: Optional[str] = None
    "State parameter passed back to the bot after authentication/configuration flow"
