"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal, Union

InputHint = Union[Literal["acceptingInput", "ignoringInput", "expectingInput"], str]
