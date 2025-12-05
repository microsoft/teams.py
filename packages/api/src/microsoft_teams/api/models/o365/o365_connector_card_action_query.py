"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from ..custom_base_model import CustomBaseModel


class O365ConnectorCardActionQuery(CustomBaseModel):
    """
    An interface representing O365ConnectorCardActionQuery.
    O365 connector card HttpPOST invoke query
    """

    body: Optional[str] = None
    """
    The results of body string defined in IO365ConnectorCardHttpPOST
    with substituted input values
    """

    action_id: Optional[str] = None
    """
    Action Id associated with the HttpPOST action
    button triggered, defined in O365ConnectorCardActionBase.
    """
