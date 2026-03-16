"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Awaitable, Callable, TypeVar, Union

from httpx import Request, Response

T = TypeVar("T")
D = TypeVar("D")


class InterceptorRequestContext:
    def __init__(self, request: Request):
        self.request = request


class InterceptorResponseContext:
    def __init__(self, response: Response):
        self.response = response


RequestInterceptor = Callable[[InterceptorRequestContext], Union[Any, Awaitable[Any]]]
ResponseInterceptor = Callable[[InterceptorResponseContext], Union[Any, Awaitable[Any]]]


class Interceptor:
    """
    Protocol for HTTP interceptors.

    Optionally implement any of:
    - request(ctx): mutate or observe outgoing request (ctx: InterceptorRequestContext)
    - response(ctx): mutate or observe incoming response (ctx: InterceptorResponseContext)
    """

    def request(self, ctx: InterceptorRequestContext) -> Union[None, Awaitable[None]]: ...

    def response(self, ctx: InterceptorResponseContext) -> Union[None, Awaitable[None]]: ...
