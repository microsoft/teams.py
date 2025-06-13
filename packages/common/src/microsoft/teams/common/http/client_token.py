"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import inspect
from typing import Awaitable, Callable, Optional, Protocol, Union, runtime_checkable


# String-like protocol: any object with __str__
@runtime_checkable
class StringLike(Protocol):
    def __str__(self) -> str: ...


TokenFactory = Callable[
    [],
    Union[
        str,
        StringLike,
        None,
        Awaitable[Union[str, StringLike, None]],
    ],
]

Token = Union[str, StringLike, TokenFactory, None]


async def resolve_token(token: Token) -> Optional[str]:
    """
    Resolves a token value to a string, handling callables and awaitables.
    Always used as an async function for uniform async usage.
    """
    value = token
    if callable(value):
        called_value = value()
        if inspect.isawaitable(called_value):
            resolved = await called_value
            return str(resolved) if resolved is not None else None
        return str(called_value) if called_value is not None else None
    if value is None:
        return None
    return str(value)
