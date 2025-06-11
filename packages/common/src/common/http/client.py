from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx

from common.http.clientToken import Token, resolve_token
from common.http.interceptor import Interceptor, InterceptorRequestContext, InterceptorResponseContext
from common.logging import ConsoleLogger, Logger


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
    headers: Optional[Dict[str, str]] = field(default_factory=dict)
    timeout: Optional[float] = None
    logger: Logger = field(default_factory=ConsoleLogger)
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
        self.options = options
        self.logger = options.logger
        self.token = options.token

        # Maintain interceptors as a separate instance attribute (do not mutate options)
        self._interceptors = list(options.interceptors or [])

        self.http = httpx.AsyncClient(
            base_url=options.base_url,
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
        req_headers = {**self.options.headers, **(headers or {})}
        resolved_token = await self._resolve_token(token)
        if resolved_token:
            req_headers["Authorization"] = f"Bearer {resolved_token}"
        return req_headers

    async def get(
        self, url: str, *, headers: Optional[Dict[str, str]] = None, token: Optional[Token] = None, **kwargs
    ) -> httpx.Response:
        """
        Send a GET request.

        Args:
            url: The URL path or full URL.
            headers: Optional per-request headers.
            token: Optional per-request token (overrides default).
            **kwargs: Additional httpx.AsyncClient.get arguments.

        Returns:
            httpx.Response
        """
        req_headers = await self._prepare_headers(headers, token)
        return await self.http.get(url, headers=req_headers, **kwargs)

    async def post(
        self,
        url: str,
        data: Any = None,
        *,
        headers: Optional[Dict[str, str]] = None,
        token: Optional[Token] = None,
        **kwargs,
    ) -> httpx.Response:
        """
        Send a POST request.

        Args:
            url: The URL path or full URL.
            data: The request body.
            headers: Optional per-request headers.
            token: Optional per-request token (overrides default).
            **kwargs: Additional httpx.AsyncClient.post arguments.

        Returns:
            httpx.Response
        """
        req_headers = await self._prepare_headers(headers, token)
        return await self.http.post(url, data=data, headers=req_headers, **kwargs)

    async def put(
        self,
        url: str,
        data: Any = None,
        *,
        headers: Optional[Dict[str, str]] = None,
        token: Optional[Token] = None,
        **kwargs,
    ) -> httpx.Response:
        """
        Send a PUT request.

        Args:
            url: The URL path or full URL.
            data: The request body.
            headers: Optional per-request headers.
            token: Optional per-request token (overrides default).
            **kwargs: Additional httpx.AsyncClient.put arguments.

        Returns:
            httpx.Response
        """
        req_headers = await self._prepare_headers(headers, token)
        return await self.http.put(url, data=data, headers=req_headers, **kwargs)

    async def patch(
        self,
        url: str,
        data: Any = None,
        *,
        headers: Optional[Dict[str, str]] = None,
        token: Optional[Token] = None,
        **kwargs,
    ) -> httpx.Response:
        """
        Send a PATCH request.

        Args:
            url: The URL path or full URL.
            data: The request body.
            headers: Optional per-request headers.
            token: Optional per-request token (overrides default).
            **kwargs: Additional httpx.AsyncClient.patch arguments.

        Returns:
            httpx.Response
        """
        req_headers = await self._prepare_headers(headers, token)
        return await self.http.patch(url, data=data, headers=req_headers, **kwargs)

    async def delete(
        self, url: str, *, headers: Optional[Dict[str, str]] = None, token: Optional[Token] = None, **kwargs
    ) -> httpx.Response:
        """
        Send a DELETE request.

        Args:
            url: The URL path or full URL.
            headers: Optional per-request headers.
            token: Optional per-request token (overrides default).
            **kwargs: Additional httpx.AsyncClient.delete arguments.

        Returns:
            httpx.Response
        """
        req_headers = await self._prepare_headers(headers, token)
        return await self.http.delete(url, headers=req_headers, **kwargs)

    async def request(
        self,
        method: str,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        token: Optional[Token] = None,
        **kwargs,
    ) -> httpx.Response:
        """
        Send a custom HTTP request.

        Args:
            method: HTTP method (GET, POST, etc).
            url: The URL path or full URL.
            headers: Optional per-request headers.
            token: Optional per-request token (overrides default).
            **kwargs: Additional httpx.AsyncClient.request arguments.

        Returns:
            httpx.Response
        """
        req_headers = await self._prepare_headers(headers, token)
        return await self.http.request(method, url, headers=req_headers, **kwargs)

    async def _resolve_token(self, token: Optional[Token]) -> Optional[str]:
        """
        Resolve the token to a string, using per-request or default token.

        Args:
            token: Per-request token or None.

        Returns:
            The resolved token string or None.
        """
        use_token = token if token is not None else self.token
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
        event_hooks_dict = {}
        for hook in self._interceptors:
            if hasattr(hook, "request"):

                def make_request_wrapper(h):
                    async def wrapper(request):
                        ctx = InterceptorRequestContext(request, self.logger)
                        result = h.request(ctx)
                        if hasattr(result, "__await__"):
                            return await result
                        return result

                    return wrapper

                event_hooks_dict.setdefault("request", []).append(make_request_wrapper(hook))
            if hasattr(hook, "response"):

                def make_response_wrapper(h):
                    async def wrapper(response):
                        ctx = InterceptorResponseContext(response, self.logger)
                        result = h.response(ctx)
                        if hasattr(result, "__await__"):
                            return await result
                        return result

                    return wrapper

                event_hooks_dict.setdefault("response", []).append(make_response_wrapper(hook))
        self.http.event_hooks = event_hooks_dict

    def clone(self, **overrides) -> "Client":
        """
        Create a new Client instance with merged configuration.

        Args:
            **overrides: Partial ClientOptions fields to override.

        Returns:
            A new Client instance with merged options and a cloned interceptor list.
        """
        # Merge options, shallow copy interceptors array
        merged_options = ClientOptions(
            base_url=overrides.get("base_url", self.options.base_url),
            headers={**self.options.headers, **overrides.get("headers", {})}
            if overrides.get("headers")
            else dict(self.options.headers),
            timeout=overrides.get("timeout", self.options.timeout),
            logger=overrides.get("logger", self.options.logger),
            token=overrides.get("token", self.options.token),
            interceptors=list(overrides.get("interceptors", self._interceptors)),
        )
        return Client(merged_options)
