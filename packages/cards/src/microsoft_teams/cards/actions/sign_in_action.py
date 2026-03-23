"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import warnings

from ..core import SigninSubmitActionData, SubmitAction, SubmitActionData


class SignInAction(SubmitAction):
    """This class is deprecated. Please use SigninSubmitActionData instead.
    This will be removed in version 2.0.0 GA."""

    def __init__(self, value: str):
        warnings.warn(
            "SignInAction is deprecated. Use SigninSubmitActionData instead. "
            "This will be removed in version 2.0.0 GA.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__()
        action_data = SigninSubmitActionData().with_value(value)
        self.data = SubmitActionData(ms_teams=action_data.model_dump())
