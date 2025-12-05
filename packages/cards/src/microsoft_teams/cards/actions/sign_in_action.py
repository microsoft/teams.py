"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from ..core import SigninSubmitActionData, SubmitAction, SubmitActionData


class SignInAction(SubmitAction):
    def __init__(self, value: str):
        super().__init__()
        action_data = SigninSubmitActionData().with_value(value)
        self.data = SubmitActionData(ms_teams=action_data.model_dump())
