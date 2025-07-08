"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Annotated, Union

from pydantic import Field

from .command_result import CommandResultActivity, CommandResultValue
from .command_send import CommandSendActivity, CommandSendValue

CommandActivity = Annotated[Union[CommandSendActivity, CommandResultActivity], Field(discriminator="type")]

__all__ = ["CommandResultValue", "CommandResultActivity", "CommandSendValue", "CommandSendActivity", "CommandActivity"]
