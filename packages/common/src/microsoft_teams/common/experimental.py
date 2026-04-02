"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import functools
import inspect
import warnings
from typing import Any, Callable, Optional, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


class ExperimentalWarning(FutureWarning):
    """Warning category for Teams SDK preview APIs.

    Preview APIs may change in the future.
    """

    pass


def experimental(diagnostic: str, *, message: Optional[str] = None) -> Callable[[F], F]:
    """Mark a class or function as a preview API.

    Emits an ExperimentalWarning when the decorated class is instantiated
    or the decorated function is called.

    Args:
        diagnostic: The diagnostic code (e.g., "ExperimentalTeamsReactions") for granular opt-in.
        message: Optional custom warning message. If not provided, a default message is used.

    Usage::

        @experimental("ExperimentalTeamsReactions")
        class ReactionClient:
            ...

        @experimental("ExperimentalTeamsTargeted", message="Targeted messages are in preview.")
        async def create_targeted(...):
            ...
    """

    def decorator(obj: F) -> F:
        name = getattr(obj, "__qualname__", getattr(obj, "__name__", str(obj)))
        warn_msg = message or (f"{name} is in preview and may change in the future. Diagnostic: {diagnostic}")

        if isinstance(obj, type):
            original_init = obj.__init__

            @functools.wraps(original_init)
            def new_init(self: Any, *args: Any, **kwargs: Any) -> None:
                warnings.warn(warn_msg, ExperimentalWarning, stacklevel=2)
                original_init(self, *args, **kwargs)

            obj.__init__ = new_init  # type: ignore[misc]
            return obj  # type: ignore[return-value]
        else:
            if inspect.iscoroutinefunction(obj):

                @functools.wraps(obj)
                async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                    warnings.warn(warn_msg, ExperimentalWarning, stacklevel=2)
                    return await obj(*args, **kwargs)

                return async_wrapper  # type: ignore[return-value]
            else:

                @functools.wraps(obj)
                def wrapper(*args: Any, **kwargs: Any) -> Any:
                    warnings.warn(warn_msg, ExperimentalWarning, stacklevel=2)
                    return obj(*args, **kwargs)

                return wrapper  # type: ignore[return-value]

    return decorator
