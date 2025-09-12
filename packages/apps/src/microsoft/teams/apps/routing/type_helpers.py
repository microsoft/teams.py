"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Awaitable, Callable, Optional, TypeVar, Union

from microsoft.teams.api import ActivityBase, InvokeResponse, InvokeResponseBody

from .activity_context import ActivityContext

# Type variables for generic activity and response types
ActivityT = TypeVar("ActivityT", bound=ActivityBase)
ResponseT = TypeVar("ResponseT", bound=InvokeResponseBody)

# Basic handler types that
BasicHandler = Callable[[ActivityContext[ActivityT]], Awaitable[Optional[Any]]]
BasicHandlerDecorator = Callable[[BasicHandler[ActivityT]], BasicHandler[ActivityT]]

# Invoke handler types that
InvokeHandler = Callable[
    [ActivityContext[ActivityT]],
    Awaitable[Union[InvokeResponse[ResponseT], ResponseT]],
]
InvokeHandlerDecorator = Callable[[InvokeHandler[ActivityT, ResponseT]], InvokeHandler[ActivityT, ResponseT]]

# Special case for handlers that return None in invoke scenarios
VoidInvokeHandler = Callable[[ActivityContext[ActivityT]], Awaitable[Union[InvokeResponse[None], None]]]
VoidInvokeHandlerDecorator = Callable[[VoidInvokeHandler[ActivityT]], VoidInvokeHandler[ActivityT]]

# Union types for overloaded methods
BasicHandlerUnion = Union[BasicHandlerDecorator[ActivityT], BasicHandler[ActivityT]]
InvokeHandlerUnion = Union[InvokeHandlerDecorator[ActivityT, ResponseT], InvokeHandler[ActivityT, ResponseT]]
VoidInvokeHandlerUnion = Union[VoidInvokeHandlerDecorator[ActivityT], VoidInvokeHandler[ActivityT]]
