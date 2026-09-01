"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import inspect
import logging
from collections import OrderedDict
from dataclasses import replace
from time import perf_counter
from typing import Any, Awaitable, Callable, Iterator, List, Mapping, Optional, Sequence, Tuple, TypeVar, Union

from httpx import HTTPStatusError
from microsoft_teams.api import GetUserTokenParams, SignOutUserParams

from .diagnostics._constants import (
    APP_ATTRIBUTE_NAMES,
    APP_OAUTH_ERROR_TYPES,
    APP_OAUTH_OPERATIONS,
    APP_OAUTH_RESULTS,
    APP_SPAN_NAMES,
)
from .diagnostics._helpers import get_tracer, record_exception, record_oauth_error, record_oauth_operation
from .events import SignInEvent, SignInFailureEvent
from .oauth_connection import connection_lookup_key, normalize_connection_name
from .oauth_state import (
    clear_pending_oauth_sign_in,
    get_pending_oauth_sign_ins,
)
from .routing import ActivityContext, SignInOptions

logger = logging.getLogger(__name__)

SignInHandler = Union[
    Callable[[SignInEvent], None],
    Callable[[SignInEvent], Awaitable[None]],
]
SignInFailureHandler = Union[
    Callable[[SignInFailureEvent], None],
    Callable[[SignInFailureEvent], Awaitable[None]],
]

# Bound to the aliases above so the decorators hand back the exact function type
# they were given instead of widening it to the union.
SignInHandlerT = TypeVar("SignInHandlerT", bound=SignInHandler)
SignInFailureHandlerT = TypeVar("SignInFailureHandlerT", bound=SignInFailureHandler)


async def _dispatch_handlers(
    handlers: Sequence[Callable[[Any], Union[None, Awaitable[None]]]],
    event: Any,
    connection_name: str,
    kind: str,
) -> None:
    """Run each handler in registration order, one fully completed before the next.

    Handlers may be sync or async, so the result is awaited only when it is
    actually awaitable. A raising handler is logged and skipped rather than
    propagated: it is a listener, and one broken listener must not hide the
    remaining ones or turn a successful callback into a failed invoke response.
    """
    for handler in tuple(handlers):
        try:
            result = handler(event)
            if inspect.isawaitable(result):
                await result
        except Exception:
            logger.exception(
                "%s handler %r failed for connection %r; continuing with later handlers.",
                kind,
                getattr(handler, "__name__", handler),
                connection_name,
            )


DEFAULT_OAUTH_CARD_TEXT = SignInOptions().oauth_card_text
DEFAULT_SIGN_IN_BUTTON_TEXT = SignInOptions().sign_in_button_text


class OAuthFlow:
    """One named OAuth connection, plus the handlers attached to it.

    Created via ``app.add_oauth_flow(...)`` — not constructed directly.
    """

    def __init__(
        self,
        connection_name: str,
        *,
        oauth_card_text: str = DEFAULT_OAUTH_CARD_TEXT,
        sign_in_button_text: str = DEFAULT_SIGN_IN_BUTTON_TEXT,
    ) -> None:
        self.connection_name = normalize_connection_name(connection_name)
        self._defaults = SignInOptions(
            oauth_card_text=oauth_card_text,
            sign_in_button_text=sign_in_button_text,
            connection_name=self.connection_name,
        )
        self._on_signin: List[SignInHandler] = []
        self._on_signin_failure: List[SignInFailureHandler] = []

    def __repr__(self) -> str:
        return f"OAuthFlow(connection_name={self.connection_name!r})"

    # -- handler registration -------------------------------------------------

    def on_signin(self, func: SignInHandlerT) -> SignInHandlerT:
        """Register a handler for a successful sign-in on this connection.

        The handler may be synchronous or asynchronous, and may be registered more
        than once. Handlers run in registration order and are isolated from one
        another: if one raises, the error is logged and the rest still run.
        """
        self._on_signin.append(func)
        return func

    def on_signin_failure(self, func: SignInFailureHandlerT) -> SignInFailureHandlerT:
        """Register a handler for a failed silent-SSO attempt on this connection.

        The handler may be synchronous or asynchronous, and may be registered more
        than once. Handlers run in registration order and are isolated from one
        another: if one raises, the error is logged and the rest still run.

        A ``signin/failure`` callback carries no connection name, so the app matches
        it against the pending sign-in recorded when the flow started. That record
        lives in durable state when state is enabled, and otherwise in a short-lived
        process-local cache. If neither resolves — most commonly because the callback
        reached a different process than the one that started the sign-in — the
        failure cannot be attributed, and **every** registered flow's failure
        handlers are notified rather than none. Handlers that must act on only their
        own connection should enable state, which makes attribution reliable across
        processes.
        """
        self._on_signin_failure.append(func)
        return func

    async def _invoke_signin_handlers(self, event: SignInEvent) -> None:
        await _dispatch_handlers(self._on_signin, event, self.connection_name, "on_signin")

    async def _invoke_signin_failure_handlers(self, event: SignInFailureEvent) -> None:
        await _dispatch_handlers(self._on_signin_failure, event, self.connection_name, "on_signin_failure")

    # -- operations -----------------------------------------------------------

    async def sign_in(self, ctx: ActivityContext[Any], options: Optional[SignInOptions] = None) -> Optional[str]:
        """Start sign-in.

        Returns a token immediately if one already exists, otherwise sends an
        OAuth card and returns ``None``. If the caller passes their own
        ``SignInOptions`` their card text wins, but the connection name is
        always forced to this flow's — you cannot accidentally sign in on the
        wrong connection through a flow object. When per-turn state is enabled,
        a pending hint is recorded so connection-less verify-state callbacks
        probe likely flows first and silent-SSO failures can be attributed to
        this flow. Without state, verify-state probes the registered flows and
        legacy default connection, while failures use the registered-flow
        fallback.
        """
        base = self._defaults if options is None else options
        result = APP_OAUTH_RESULTS.failure
        started_at = perf_counter()
        try:
            with get_tracer().start_as_current_span(
                APP_SPAN_NAMES.oauth_signin,
                record_exception=False,
                set_status_on_exception=False,
            ) as span:
                span.set_attribute(APP_ATTRIBUTE_NAMES.oauth_connection, self.connection_name)
                span.set_attribute(APP_ATTRIBUTE_NAMES.oauth_operation, APP_OAUTH_OPERATIONS.signin)
                try:
                    token = await ctx.sign_in(replace(base, connection_name=self.connection_name))
                except Exception as exception:
                    error_type = (
                        APP_OAUTH_ERROR_TYPES.http_error
                        if isinstance(exception, HTTPStatusError)
                        else APP_OAUTH_ERROR_TYPES.exception
                    )
                    span.set_attribute(APP_ATTRIBUTE_NAMES.oauth_error_type, error_type)
                    span.set_attribute(APP_ATTRIBUTE_NAMES.oauth_result, result)
                    record_exception(span, exception)
                    record_oauth_error(self.connection_name, APP_OAUTH_OPERATIONS.signin, error_type)
                    raise

                result = APP_OAUTH_RESULTS.cached if token is not None else APP_OAUTH_RESULTS.card_sent
                span.set_attribute(APP_ATTRIBUTE_NAMES.oauth_result, result)
                return token
        finally:
            record_oauth_operation(
                self.connection_name,
                APP_OAUTH_OPERATIONS.signin,
                result,
                (perf_counter() - started_at) * 1000,
            )

    async def sign_out(self, ctx: ActivityContext[Any]) -> None:
        """Sign the user out of this connection."""
        await ctx.api.users.sign_out(
            SignOutUserParams(
                channel_id=ctx.activity.channel_id,
                user_id=ctx.activity.from_.id,
                connection_name=self.connection_name,
            )
        )

    async def get_token(self, ctx: ActivityContext[Any]) -> Optional[str]:
        """The user's token for this connection, or ``None`` if not signed in."""
        try:
            res = await ctx.api.users.get_token(
                GetUserTokenParams(
                    channel_id=ctx.activity.channel_id,
                    user_id=ctx.activity.from_.id,
                    connection_name=self.connection_name,
                )
            )
            return res.token
        except HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise

    async def is_signed_in(self, ctx: ActivityContext[Any]) -> bool:
        """Whether the user currently has a token for this connection."""
        return await self.get_token(ctx) is not None


class OAuthFlowRegistry(Mapping[str, OAuthFlow]):
    """Case-insensitive, insertion-ordered collection of ``OAuthFlow``.

    Subclasses ``Mapping``, so ``in``, ``.get()``, ``.values()``, ``len()`` and
    truthiness all work without extra code.
    """

    def __init__(self) -> None:
        self._flows: "OrderedDict[str, OAuthFlow]" = OrderedDict()

    def __getitem__(self, connection_name: str) -> OAuthFlow:
        key = connection_lookup_key(connection_name)
        if key is None:
            # Blank or non-string names address nothing. Raising ``KeyError``
            # rather than ``ValueError`` keeps ``.get()`` and ``in`` working.
            raise KeyError(connection_name)
        return self._flows[key]

    def __iter__(self) -> Iterator[str]:
        return (flow.connection_name for flow in self._flows.values())

    def __len__(self) -> int:
        return len(self._flows)

    def add(self, flow: OAuthFlow) -> OAuthFlow:
        """Register a flow. Raises ``ValueError`` if the connection already exists."""
        key = normalize_connection_name(flow.connection_name).lower()
        if key in self._flows:
            raise ValueError(
                f"An OAuth flow for connection '{flow.connection_name}' is already "
                f"registered. Connection names are case-insensitive."
            )
        self._flows[key] = flow
        return flow

    def _pending_flows(self, ctx: ActivityContext[Any], *, sso_only: bool = False) -> List[OAuthFlow]:
        conversation_id, user_id = _pending_scope(ctx)
        flows: List[OAuthFlow] = []
        for pending in get_pending_oauth_sign_ins(ctx.state, conversation_id, user_id):
            if sso_only and not pending.sso_offered:
                continue
            flow = self.get(pending.connection_name)
            if flow is None:
                # Expected whenever ``ctx.sign_in()`` was used without registering a flow
                # (the legacy default-connection app), so this is not a warning.
                logger.debug(
                    "Discarding pending OAuth sign-in state for connection '%s': no registered OAuth flow.",
                    pending.connection_name,
                )
                clear_pending_oauth_sign_in(ctx.state, pending.connection_name, conversation_id, user_id)
                continue
            flows.append(flow)
        return flows

    def _clear_pending(self, ctx: ActivityContext[Any], connection_name: Optional[str] = None) -> None:
        conversation_id, user_id = _pending_scope(ctx)
        clear_pending_oauth_sign_in(ctx.state, connection_name, conversation_id, user_id)


def _pending_scope(ctx: ActivityContext[Any]) -> Tuple[Optional[str], Optional[str]]:
    """Conversation and user identifiers used to scope process-local pending hints."""
    conversation = getattr(ctx.activity, "conversation", None)
    sender = getattr(ctx.activity, "from_", None)
    return getattr(conversation, "id", None), getattr(sender, "id", None)
