import inspect
import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional

import httpx
from httpx._models import Request, Response
from httpx._types import QueryParamTypes, RequestContent, RequestData, RequestFiles

from common.http.client_token import Token, resolve_token
from common.http.interceptor import Interceptor, InterceptorRequestContext, InterceptorResponseContext
from common.logging import ConsoleLogger

console_logger = ConsoleLogger()


@dataclass(frozen=True)
class ClientOptions:
    """
    Configuration options for the HTTP Client.

    Attributes:
        base_url: The base URL for all requests.
        headers: Default headers to include with every request.
        timeout: Default request timeout in seconds.
        logger: Logger instance for request/response/error logging.
        token: Default authorization token (string, string-like, or callable).
        interceptors: List of interceptors for request/response middleware.
    """

    base_url: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)
    timeout: Optional[float] = None
    logger: logging.Logger = field(default_factory=lambda: console_logger.create_logger("http-client"))
    token: Optional[Token] = None
    interceptors: Optional[List[Interceptor]] = field(default_factory=list)


class Client:
    """
    HTTP Client abstraction for making requests with configurable options.

    Args:
        options: ClientOptions dataclass with configuration for the client.
    """

    def __init__(self, options: ClientOptions):
        """
        Initialize the HTTP Client.

        Args:
            options: ClientOptions dataclass with configuration for the client.
        """
        self._options = options
        self._logger = options.logger
        self._token = options.token

        # Maintain interceptors as a separate instance attribute (do not mutate options)
        self._interceptors = list(options.interceptors or [])

        self.http = httpx.AsyncClient(
            base_url=httpx.URL(options.base_url) if options.base_url else "",
            headers=options.headers,
            timeout=options.timeout,
        )
        self._update_event_hooks()

    async def _prepare_headers(self, headers: Optional[Dict[str, str]], token: Optional[Token]) -> Dict[str, str]:
        """
        Merge default and per-request headers, resolve token, and inject Authorization header if needed.

        Args:
            headers: Optional per-request headers.
            token: Optional per-request token.

        Returns:
            Final headers dict for the request.
        """
        req_headers = {**self._options.headers, **(headers or {})}
        resolved_token = await self._resolve_token(token)
        if resolved_token:
            req_headers["Authorization"] = f"Bearer {resolved_token}"
        return req_headers

    async def get(
        self,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        token: Optional[Token] = None,
        params: Optional[QueryParamTypes] = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """
        Send a GET request.

        Args:
            url: The URL path or full URL.
            headers: Optional per-request headers.
            params: Optional query parameters.
            token: Optional per-request token (overrides default).
            **kwargs: Additional httpx.AsyncClient.get arguments.

        Returns:
            httpx.Response
        """
        req_headers = await self._prepare_headers(headers, token)
        return await self.http.get(url, headers=req_headers, params=params, **kwargs)

    async def post(
        self,
        url: str,
        *,
        content: Optional[RequestContent] = None,
        data: Optional[RequestData] = None,
        files: Optional[RequestFiles] = None,
        json: Optional[Any] = None,
        params: Optional[QueryParamTypes] = None,
        headers: Optional[Dict[str, str]] = None,
        token: Optional[Token] = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """
        Send a POST request.

        Args:
            url: The URL path or full URL.
            data: The request body.
            headers: Optional per-request headers.
            params: Optional query parameters.
            content: The request body.
            files: The request files.
            json: The request JSON body.
            token: Optional per-request token (overrides default).
            **kwargs: Additional httpx.AsyncClient.post arguments.

        Returns:
            httpx.Response
        """
        req_headers = await self._prepare_headers(headers, token)
        return await self.http.post(
            url,
            data=data,
            files=files,
            json=json,
            content=content,
            params=params,
            headers=req_headers,
            **kwargs,
        )

    async def put(
        self,
        url: str,
        *,
        content: Optional[RequestContent] = None,
        data: Optional[RequestData] = None,
        files: Optional[RequestFiles] = None,
        json: Optional[Any] = None,
        params: Optional[QueryParamTypes] = None,
        headers: Optional[Dict[str, str]] = None,
        token: Optional[Token] = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """
        Send a PUT request.

        Args:
            url: The URL path or full URL.
            data: The request body.
            headers: Optional per-request headers.
            params: Optional query parameters.
            content: The request body.
            files: The request files.
            json: The request JSON body.
            token: Optional per-request token (overrides default).
            **kwargs: Additional httpx.AsyncClient.put arguments.

        Returns:
            httpx.Response
        """
        req_headers = await self._prepare_headers(headers, token)
        return await self.http.put(
            url,
            data=data,
            files=files,
            json=json,
            content=content,
            params=params,
            headers=req_headers,
            **kwargs,
        )

    async def patch(
        self,
        url: str,
        *,
        content: Optional[RequestContent] = None,
        data: Optional[RequestData] = None,
        files: Optional[RequestFiles] = None,
        json: Optional[Any] = None,
        params: Optional[QueryParamTypes] = None,
        headers: Optional[Dict[str, str]] = None,
        token: Optional[Token] = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """
        Send a PATCH request.

        Args:
            url: The URL path or full URL.
            data: The request body.
            headers: Optional per-request headers.
            params: Optional query parameters.
            content: The request body.
            files: The request files.
            json: The request JSON body.
            token: Optional per-request token (overrides default).
            **kwargs: Additional httpx.AsyncClient.patch arguments.

        Returns:
            httpx.Response
        """
        req_headers = await self._prepare_headers(headers, token)
        return await self.http.patch(
            url,
            data=data,
            files=files,
            json=json,
            content=content,
            params=params,
            headers=req_headers,
            **kwargs,
        )

    async def delete(
        self,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        token: Optional[Token] = None,
        params: Optional[QueryParamTypes] = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """
        Send a DELETE request.

        Args:
            url: The URL path or full URL.
            headers: Optional per-request headers.
            params: Optional query parameters.
            token: Optional per-request token (overrides default).
            **kwargs: Additional httpx.AsyncClient.delete arguments.

        Returns:
            httpx.Response
        """
        req_headers = await self._prepare_headers(headers, token)
        return await self.http.delete(url, headers=req_headers, params=params, **kwargs)

    async def request(
        self,
        method: str,
        url: str,
        *,
        params: Optional[QueryParamTypes] = None,
        headers: Optional[Dict[str, str]] = None,
        token: Optional[Token] = None,
        content: Optional[RequestContent] = None,
        data: Optional[RequestData] = None,
        files: Optional[RequestFiles] = None,
        json: Optional[Any] = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """
        Send a custom HTTP request.

        Args:
            method: HTTP method (GET, POST, etc).
            url: The URL path or full URL.
            headers: Optional per-request headers.
            params: Optional query parameters.
            content: The request body.
            data: The request body.
            files: The request files.
            json: The request JSON body.
            token: Optional per-request token (overrides default).
            **kwargs: Additional httpx.AsyncClient.request arguments.

        Returns:
            httpx.Response
        """
        req_headers = await self._prepare_headers(headers, token)
        return await self.http.request(
            method,
            url,
            headers=req_headers,
            params=params,
            content=content,
            data=data,
            files=files,
            json=json,
            **kwargs,
        )

    async def _resolve_token(self, token: Optional[Token]) -> Optional[str]:
        """
        Resolve the token to a string, using per-request or default token.

        Args:
            token: Per-request token or None.

        Returns:
            The resolved token string or None.
        """
        use_token = token if token is not None else self._token
        if use_token is None:
            return None
        return await resolve_token(use_token)

    def use_interceptor(self, interceptor: Interceptor) -> None:
        """
        Register an interceptor for request/response middleware.

        Args:
            interceptor: An object with optional request/response methods.
        """
        self._interceptors.append(interceptor)
        self._update_event_hooks()

    def _update_event_hooks(self) -> None:
        """
        Internal: Update the httpx.AsyncClient event_hooks to match current interceptors.
        """
        event_hooks_dict: Dict[str, List[Callable[[Any], Any]]] = {}
        for hook in self._interceptors:
            if hasattr(hook, "request"):

                def _make_request_wrapper(h: Interceptor) -> Callable[[Request], Awaitable[None]]:
                    async def wrapper(request: Request) -> None:
                        ctx = InterceptorRequestContext(request, self._logger)
                        result = h.request(ctx)
                        if inspect.isawaitable(result):
                            await result

                    return wrapper

                event_hooks_dict.setdefault("request", []).append(_make_request_wrapper(hook))
            if hasattr(hook, "response"):

                def _make_response_wrapper(h: Interceptor) -> Callable[[Response], Awaitable[None]]:
                    async def wrapper(response: Response) -> None:
                        ctx = InterceptorResponseContext(response, self._logger)
                        result = h.response(ctx)
                        if inspect.isawaitable(result):
                            await result

                    return wrapper

                event_hooks_dict.setdefault("response", []).append(_make_response_wrapper(hook))
        self.http.event_hooks = event_hooks_dict

    def clone(self, overrides: Optional[ClientOptions] = None) -> "Client":
        """
        Create a new Client instance with merged configuration.

        Args:
            overrides: Optional ClientOptions object to override fields.

        Returns:
            A new Client instance with merged options and a cloned interceptor list.
        """
        overrides = overrides or ClientOptions()
        merged_options = ClientOptions(
            base_url=overrides.base_url if overrides.base_url is not None else self._options.base_url,
            headers={**self._options.headers, **(overrides.headers or {})},
            timeout=overrides.timeout if overrides.timeout is not None else self._options.timeout,
            logger=overrides.logger if overrides.logger is not None else self._options.logger,
            token=overrides.token if overrides.token is not None else self._options.token,
            interceptors=list(overrides.interceptors)
            if overrides.interceptors is not None
            else list(self._interceptors),
        )
        return Client(merged_options)
