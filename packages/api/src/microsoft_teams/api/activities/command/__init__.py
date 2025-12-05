"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Annotated, Union

from pydantic import Field

from .command_result import CommandResultActivity, CommandResultActivityInput, CommandResultValue
from .command_send import CommandSendActivity, CommandSendActivityInput, CommandSendValue

CommandActivity = Annotated[Union[CommandSendActivity, CommandResultActivity], Field(discriminator="type")]

__all__ = [
    "CommandResultValue",
    "CommandResultActivity",
    "CommandResultActivityInput",
    "CommandSendValue",
    "CommandSendActivity",
    "CommandSendActivityInput",
    "CommandActivity",
]
