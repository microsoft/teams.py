"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from ..custom_base_model import CustomBaseModel


class BatchOperationResult(CustomBaseModel):
    """
    Result of a batch conversation operation, containing the operation ID
    that can be used to poll for status or cancel the operation.
    """

    operation_id: str
    "The ID of the created batch operation."
