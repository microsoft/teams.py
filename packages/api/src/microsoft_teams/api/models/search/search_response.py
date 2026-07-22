"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import List, Literal

from ..custom_base_model import CustomBaseModel


class SearchInvokeResult(CustomBaseModel):
    """
    A single result returned in a SearchResponse. For Adaptive Card dynamic typeahead
    'Input.ChoiceSet', 'title' is the display text and 'value' is the submitted value.
    """

    title: str
    "The display text of the result."

    value: str
    "The value submitted when the result is selected."


class SearchInvokeResponseValue(CustomBaseModel):
    """
    The value payload of a SearchResponse.
    """

    results: List[SearchInvokeResult]
    "The list of search results."


class SearchResponse(CustomBaseModel):
    """
    Defines the structure returned as the result of an Invoke activity with Name of
    'application/search'.
    """

    status_code: int = 200
    "The response status code."

    type: Literal["application/vnd.microsoft.search.searchResponse"] = "application/vnd.microsoft.search.searchResponse"
    "The type of this response."

    value: SearchInvokeResponseValue
    "The response value."
