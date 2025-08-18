"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from dataclasses import dataclass


@dataclass
class Page:
    """
    A custom page that can be added to DevTools.
    """

    name: str
    "The unique name of the view (must be URL safe)"

    display_name: str
    "The display name of the view to be shown in the view header"

    url: str
    "The URL of the view"

    # TODO: Uncomment once cards package is complete.
    # icon: Optional[IconName] = None
    # "An optional incon name to be shown in the view header."
