"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import inspect
from logging import Logger
from typing import Any, Callable, Optional

from .activity_context import ActivityContext


def validate_handler_type(
    logger: Logger,
    func: Callable[[Any], Any],
    expected_activity_type: Any,
    method_name: str,
    expected_type_name: Optional[str] = None,
) -> None:
    """
    Validate that a handler function has the correct type annotation.

    Args:
        func: The handler function to validate
        expected_activity_type: The expected activity type (e.g., MessageActivity)
        method_name: The name of the registration method (e.g., "onMessage")
        expected_type_name: The display name for the expected type (e.g., "InvokeActivity")

    Raises:
        TypeError: If the handler has incorrect type annotations
    """
    try:
        # Get raw type annotations without evaluation
        sig = inspect.signature(func)
        params = list(sig.parameters.values())

        if params and params[0].annotation != inspect.Parameter.empty:
            param_type = params[0].annotation

            # Check if it's Context[SomeActivity]
            if hasattr(param_type, "__origin__") and hasattr(param_type, "__args__"):
                if param_type.__origin__ is ActivityContext and param_type.__args__:
                    actual_activity_type = param_type.__args__[0]

                    if actual_activity_type != expected_activity_type:
                        # Get names for the error message
                        actual_name = getattr(actual_activity_type, "__name__", str(actual_activity_type))
                        if actual_name == "Annotated":
                            # For complex types, try to find a better name in the string
                            actual_str = str(actual_activity_type)
                            if "InvokeActivity" in actual_str:
                                actual_name = "InvokeActivity"

                        expected_name = expected_type_name or getattr(
                            expected_activity_type, "__name__", str(expected_activity_type)
                        )

                        raise TypeError(
                            f"Handler {func.__name__} expects Context[{actual_name}] "
                            f"but {method_name} requires Context[{expected_name}]"
                        )
    except TypeError:
        # Re-raise TypeError (our validation error)
        raise
    except Exception as e:
        # Other exceptions are just warnings (e.g., complex type resolution issues)
        logger.warning(f"Could not validate types for handler {func.__name__}: {e}")
