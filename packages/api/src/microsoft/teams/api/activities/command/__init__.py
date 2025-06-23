"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import TypeVar, Union

from .command_result import CommandResultActivity, CommandResultValue
from .command_send import CommandSendActivity, CommandValue

T = TypeVar("T", bound=str)
CommandActivity = Union[CommandSendActivity[T], CommandResultActivity[T]]

__all__ = ["CommandResultValue", "CommandResultActivity", "CommandValue", "CommandSendActivity", "CommandActivity"]
