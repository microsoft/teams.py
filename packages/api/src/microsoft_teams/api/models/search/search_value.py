"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Literal, Optional

from ..custom_base_model import CustomBaseModel

SearchInvokeType = Literal["search", "searchAnswer", "typeahead"]
"""The kind of search invoke value. Must be either search, searchAnswer, or typeahead."""


class SearchInvokeOptions(CustomBaseModel):
    """
    Defines the query options for an Invoke activity with Name of 'application/search'.
    """

    skip: Optional[int] = None
    "The starting reference number from which ordered search results should be returned."

    top: Optional[int] = None
    "The number of search results that should be returned."


class SearchInvokeValue(CustomBaseModel):
    """
    Defines the structure that arrives in the Activity.Value for an Invoke activity with
    Name of 'application/search'. Sent by Adaptive Card dynamic typeahead 'Input.ChoiceSet'
    inputs (via 'choices.data' / 'Data.Query').
    """

    kind: Optional[SearchInvokeType] = None
    """The kind for this search invoke value (search, searchAnswer, or typeahead). Omitted by
    Adaptive Card dynamic typeahead 'Input.ChoiceSet' inputs, so this may be None."""

    query_text: str
    "The query text of this search invoke value."

    query_options: Optional[SearchInvokeOptions] = None
    "The query options for this search invoke."

    context: Optional[Any] = None
    "Context information about the query, such as the UI control that issued the query."

    dataset: Optional[str] = None
    "The identifier of the dataset from which to fetch the choices, as authored on the Adaptive Card 'Data.Query'."
