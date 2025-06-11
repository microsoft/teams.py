import asyncio
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


def resolve_token(token: Token) -> Awaitable[Optional[str]]:
    """
    Resolves a token value to a string, handling callables and awaitables.
    Always returns an awaitable for uniform async usage.
    """

    async def _resolve():
        value = token
        if callable(value):
            value = value()
            if asyncio.iscoroutine(value):
                value = await value
        if value is None:
            return None
        return str(value)

    return _resolve()
