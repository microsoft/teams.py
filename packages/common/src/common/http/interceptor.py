from typing import Any, Awaitable, Callable, TypeVar, Union

from httpx import Request, Response

from common.logging import Logger

T = TypeVar("T")
D = TypeVar("D")


class InterceptorRequestContext:
    def __init__(self, request: Request, log: Logger):
        self.request = request
        self.log = log


class InterceptorResponseContext:
    def __init__(self, response: Response, log: Logger):
        self.response = response
        self.log = log


RequestInterceptor = Callable[[InterceptorRequestContext], Union[Any, Awaitable[Any]]]
ResponseInterceptor = Callable[[InterceptorResponseContext], Union[Any, Awaitable[Any]]]


class Interceptor:
    """
    Protocol for HTTP interceptors.

    Optionally implement any of:
    - request(ctx): mutate or observe outgoing request (ctx: InterceptorRequestContext)
    - response(ctx): mutate or observe incoming response (ctx: InterceptorResponseContext)
    """

    def request(self, ctx: InterceptorRequestContext) -> Union[Any, Awaitable[Any]]: ...

    def response(self, ctx: InterceptorResponseContext) -> Union[Any, Awaitable[Any]]: ...
