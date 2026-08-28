"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import logging
from asyncio import Future
from dataclasses import dataclass
from time import perf_counter, time
from typing import Dict, Optional, Union

from httpx import HTTPStatusError
from microsoft_teams.api import (
    ExchangeUserTokenParams,
    GetUserTokenParams,
    InvokeResponse,
    SignInFailureInvokeActivity,
    SignInTokenExchangeInvokeActivity,
    SignInVerifyStateInvokeActivity,
    TokenExchangeInvokeResponse,
    TokenExchangeInvokeResponseType,
    TokenExchangeRequest,
)
from microsoft_teams.common import EventEmitter

from .diagnostics._constants import (
    APP_ATTRIBUTE_NAMES,
    APP_OAUTH_ERROR_TYPES,
    APP_OAUTH_OPERATIONS,
    APP_OAUTH_RESULTS,
    APP_SPAN_NAMES,
)
from .diagnostics._helpers import get_tracer, record_exception, record_oauth_error, record_oauth_operation
from .events import ErrorEvent, EventType, SignInEvent, SignInFailureEvent
from .oauth_connection import connection_lookup_key
from .oauth_flow import OAuthFlow, OAuthFlowRegistry
from .oauth_state import (
    TOKEN_EXCHANGE_DEDUP_TTL_SECONDS,
    has_completed_token_exchange,
    record_completed_token_exchange,
)
from .routing import ActivityContext

logger = logging.getLogger(__name__)

TokenExchangeResult = Union[TokenExchangeInvokeResponseType, InvokeResponse[TokenExchangeInvokeResponseType]]

_TOKEN_EXCHANGE_DEDUP_MAX_ENTRIES = 1000
"""Cap on the in-memory completed-marker set, so a long-lived process cannot grow it
without bound even if entries are added faster than the TTL retires them."""


@dataclass(frozen=True)
class _TokenExchangeOutcome:
    """How an owned token exchange settled, replayed to concurrent duplicates."""

    response: TokenExchangeResult = None
    error: Optional[BaseException] = None
    token_redeemed: bool = False


class OauthHandlers:
    def __init__(
        self,
        default_connection_name: str,
        event_emitter: EventEmitter[EventType],
        oauth_registry: OAuthFlowRegistry,
    ) -> None:
        self.default_connection_name = default_connection_name
        self.event_emitter = event_emitter
        self.oauth_registry = oauth_registry
        # Dedup bookkeeping is per-``App`` instance state rather than module-level
        # globals, so two apps in one process (and two tests in one session) never
        # short-circuit each other's exchanges.
        self._token_exchange_in_flight: Dict[str, Future[_TokenExchangeOutcome]] = {}
        self._token_exchange_completed: Dict[str, float] = {}

    async def sign_in_token_exchange(
        self, ctx: ActivityContext[SignInTokenExchangeInvokeActivity]
    ) -> TokenExchangeResult:
        """Handle ``signin/tokenExchange``, deduplicating repeats of the same exchange.

        Teams fans the same exchange out to every signed-in client endpoint, so the
        bot can see it several times. Duplicates short-circuit to a ``200`` no-op and
        deliberately skip ``ctx.next()``: the whole point of dedup is that the sign-in
        side effects — the ``sign_in`` event, the flow callbacks, and the rest of the
        middleware chain — run exactly once per exchange.
        """
        exchange_id = ctx.activity.value.id
        if not exchange_id:
            # Teams normally stamps every exchange with an id. Without one there is
            # nothing safe to key on, and collapsing every id-less exchange onto a
            # shared empty key would drop unrelated sign-ins, so run undeduplicated.
            return await self._run_token_exchange(ctx)

        # Claim the exchange. The in-flight lookup, the in-flight insert and the
        # completed-marker check below contain no ``await``, so the event loop cannot
        # switch coroutines part way through: on a single loop this claim is atomic,
        # which is what stops two concurrent duplicates from both starting an exchange.
        #
        # In-flight is checked first so a running exchange always wins over its own
        # completed marker. The marker is stamped the moment the token is redeemed,
        # while the owner still has sign-in callbacks to run, and a duplicate that
        # landed in that window must mirror the owner rather than answer ahead of it.
        in_flight = self._token_exchange_in_flight.get(exchange_id)
        if in_flight is not None:
            return await self._await_token_exchange(ctx, exchange_id, in_flight)
        if self._is_completed_token_exchange(ctx, exchange_id):
            return self._replay_completed_token_exchange(ctx, exchange_id)
        owned: Future[_TokenExchangeOutcome] = asyncio.get_running_loop().create_future()
        self._token_exchange_in_flight[exchange_id] = owned

        try:
            response = await self._run_token_exchange(ctx)
        except BaseException as error:
            # ``BaseException`` so cancellation also releases the entry and wakes
            # waiters, instead of leaking the id until the process restarts.
            self._settle_token_exchange(
                exchange_id,
                owned,
                # ``token_redeemed`` matters on this path too: the exchange can fail
                # *after* the token was already spent, and a waiter that does not know
                # the marker was written would let its own stale snapshot erase it.
                _TokenExchangeOutcome(
                    error=error,
                    token_redeemed=exchange_id in self._token_exchange_completed,
                ),
            )
            raise
        self._settle_token_exchange(
            exchange_id,
            owned,
            _TokenExchangeOutcome(
                response=response,
                token_redeemed=exchange_id in self._token_exchange_completed,
            ),
        )
        return response

    async def _run_token_exchange(self, ctx: ActivityContext[SignInTokenExchangeInvokeActivity]) -> TokenExchangeResult:
        """Perform the exchange itself for the request that owns this exchange id."""
        activity = ctx.activity
        api = ctx.api
        next_handler = ctx.next
        connection_name = activity.value.connection_name
        # Resolved before the ``try`` so the ``finally`` below can always report it. The
        # lookup is a plain dict access; computing it inside the ``try`` left it unbound
        # whenever anything above it raised, which would turn the metric write in
        # ``finally`` into an ``UnboundLocalError`` masking the original exception.
        flow = self.oauth_registry.get(connection_name)
        # Teams echoes back whatever casing the sign-in card carried, so telemetry keyed
        # on the raw name splits one connection into several series. ``connection_name``
        # stays raw: it is what goes on the wire to the Token Service, and rewriting that
        # would be a behavior change rather than a telemetry fix.
        event_connection_name = flow.connection_name if flow is not None else connection_name
        result = APP_OAUTH_RESULTS.failure
        started_at = perf_counter()
        try:
            with get_tracer().start_as_current_span(
                APP_SPAN_NAMES.oauth_token_exchange,
                record_exception=False,
                set_status_on_exception=False,
            ) as span:
                span.set_attribute(APP_ATTRIBUTE_NAMES.oauth_connection, event_connection_name)
                span.set_attribute(APP_ATTRIBUTE_NAMES.oauth_operation, APP_OAUTH_OPERATIONS.token_exchange)

                if (
                    connection_lookup_key(connection_name) != connection_lookup_key(self.default_connection_name)
                    and flow is None
                ):
                    logger.warning(
                        f"Sign-in token exchange invoked with connection name '{connection_name}', "
                        f"but it is neither the default connection '{self.default_connection_name}' "
                        f"nor a registered OAuth flow. "
                        f"Token verification will likely fail."
                    )

                try:
                    token = await api.users.exchange_token(
                        ExchangeUserTokenParams(
                            connection_name=connection_name,
                            user_id=activity.from_.id,
                            channel_id=activity.channel_id,
                            exchange_request=TokenExchangeRequest(
                                token=activity.value.token,
                            ),
                        )
                    )
                except HTTPStatusError as e:
                    status = e.response.status_code
                    if status not in (404, 400, 412):
                        logger.error(
                            f"Error exchanging token for user {activity.from_.id} in "
                            f"conversation {activity.conversation.id}: {e}"
                        )
                        await self.event_emitter.emit_async(
                            "error",
                            ErrorEvent(error=e, context={"activity": activity}),
                        )
                        error_type = APP_OAUTH_ERROR_TYPES.http_error
                        span.set_attribute(APP_ATTRIBUTE_NAMES.oauth_error_type, error_type)
                        record_exception(span, e)
                        record_oauth_error(event_connection_name, APP_OAUTH_OPERATIONS.token_exchange, error_type)
                        status = status or 500
                        result = APP_OAUTH_RESULTS.failure
                        span.set_attribute(APP_ATTRIBUTE_NAMES.invoke_response_status, status)
                        span.set_attribute(APP_ATTRIBUTE_NAMES.oauth_result, result)
                        return InvokeResponse(status=status)

                    # An expected miss: the Token Service has nothing to exchange.
                    # Teams reads the 412 as "fall back to the sign-in button".
                    logger.info(
                        f"Unable to exchange token for user {activity.from_.id} in "
                        f"conversation {activity.conversation.id}: {e}"
                    )
                    result = APP_OAUTH_RESULTS.failure
                    span.set_attribute(APP_ATTRIBUTE_NAMES.invoke_response_status, 412)
                    span.set_attribute(APP_ATTRIBUTE_NAMES.oauth_result, result)
                    return InvokeResponse(
                        status=412,
                        body=TokenExchangeInvokeResponse(
                            id=activity.value.id,
                            connection_name=connection_name,
                            failure_detail=str(e) or "unable to exchange token...",
                        ),
                    )
                except Exception as e:
                    # Not a Token Service rejection - a transport fault or a bug.
                    # Reporting it as 412 would tell Teams the exchange merely
                    # missed and hide a real outage, so it propagates instead and
                    # the app's own error handling reports it exactly once.
                    logger.error(
                        f"Unable to exchange token for user {activity.from_.id} in "
                        f"conversation {activity.conversation.id}: {e}"
                    )
                    error_type = APP_OAUTH_ERROR_TYPES.exception
                    span.set_attribute(APP_ATTRIBUTE_NAMES.oauth_error_type, error_type)
                    record_exception(span, e)
                    record_oauth_error(event_connection_name, APP_OAUTH_OPERATIONS.token_exchange, error_type)
                    result = APP_OAUTH_RESULTS.failure
                    span.set_attribute(APP_ATTRIBUTE_NAMES.oauth_result, result)
                    raise

                # Recorded as soon as the exchange succeeds, before any sign-in side
                # effects: the exchange token is spent at this point, so a retry could
                # never succeed anyway. A failed exchange is never marked, leaving the
                # id free for a genuine retry.
                await self._record_completed_token_exchange(ctx, activity.value.id)
                ctx.is_signed_in = True
                ctx.user_token = token.token
                self.oauth_registry._clear_pending(  # pyright: ignore[reportPrivateUsage]
                    ctx, event_connection_name
                )
                event = SignInEvent(
                    activity_ctx=ctx,
                    token_response=token,
                    connection_name=event_connection_name,
                )
                result = APP_OAUTH_RESULTS.success
                span.set_attribute(APP_ATTRIBUTE_NAMES.oauth_callback_invoked, True)
                span.set_attribute(APP_ATTRIBUTE_NAMES.oauth_result, result)
                await self.event_emitter.emit_async("sign_in", event)
                if flow is not None:
                    await flow._invoke_signin_handlers(event)  # pyright: ignore[reportPrivateUsage]
                return None
        finally:
            record_oauth_operation(
                event_connection_name,
                APP_OAUTH_OPERATIONS.token_exchange,
                result,
                (perf_counter() - started_at) * 1000,
            )
            await next_handler()

    def _is_completed_token_exchange(
        self, ctx: ActivityContext[SignInTokenExchangeInvokeActivity], exchange_id: str
    ) -> bool:
        self._prune_completed_token_exchanges()
        if exchange_id in self._token_exchange_completed:
            return True
        return self._read_persisted_marker(ctx, exchange_id)

    def _resolved_connection_name(self, connection_name: str) -> str:
        """The registered casing for ``connection_name``.

        Teams echoes back whatever casing the sign-in card carried, so the same
        connection can arrive as ``Graph`` on one request and ``graph`` on the next.
        The duplicate paths report this name to telemetry, and an unresolved name
        would split one connection into several series.

        Resolution is a registry dict lookup, exactly what ``_run_token_exchange``
        does for ``event_connection_name``. Note that ``_run_token_exchange`` still
        reports the *raw* name to its own telemetry; making that consistent is a
        wider change than this dedup path and is deliberately left alone here.
        """
        flow = self.oauth_registry.get(connection_name)
        return flow.connection_name if flow is not None else connection_name

    def _read_persisted_marker(self, ctx: ActivityContext[SignInTokenExchangeInvokeActivity], exchange_id: str) -> bool:
        """Read the cross-instance marker without ever failing the turn.

        This runs before the owning request reaches ``_run_token_exchange``'s
        ``try``/``finally``, so an escaping state error would skip ``ctx.next()`` and
        stall the middleware chain. The persisted layer is best-effort by design -- the
        in-memory guard is the authoritative same-instance one -- so an unreadable
        store degrades to in-memory-only dedup rather than taking the turn down.

        ``Exception``, not ``BaseException``: a cancellation still belongs to the task.
        """
        try:
            return has_completed_token_exchange(ctx.state, exchange_id)
        except Exception:
            logger.exception("Unable to read persisted OAuth token exchange state; deduplicating in memory only.")
            return False

    async def _record_completed_token_exchange(
        self, ctx: ActivityContext[SignInTokenExchangeInvokeActivity], exchange_id: str
    ) -> None:
        if not exchange_id:
            return

        self._prune_completed_token_exchanges()
        self._token_exchange_completed[exchange_id] = time()
        while len(self._token_exchange_completed) > _TOKEN_EXCHANGE_DEDUP_MAX_ENTRIES:
            del self._token_exchange_completed[next(iter(self._token_exchange_completed))]
        # Persisted too, so a duplicate handled by another process instance still sees
        # it. Best-effort only: state has no compare-and-set, so the in-memory layer
        # above remains the authoritative same-instance guard.
        #
        # Flushed mid-turn rather than at end of turn: the owner still has sign-in
        # callbacks to run, and a duplicate racing on another instance would otherwise
        # load a snapshot with no marker and redeem the exchange a second time. This
        # mirrors the mid-turn save ``ctx.sign_in()`` performs for its pending hint.
        try:
            record_completed_token_exchange(ctx.state, exchange_id)
            if ctx.state is not None:
                await ctx.state._save()  # pyright: ignore[reportPrivateUsage]
        except Exception:
            logger.exception("Unable to persist completed OAuth token exchange; deduplicating in memory only.")

    def _prune_completed_token_exchanges(self) -> None:
        cutoff = time() - TOKEN_EXCHANGE_DEDUP_TTL_SECONDS
        expired = [
            exchange_id
            for exchange_id, completed_at in self._token_exchange_completed.items()
            if completed_at <= cutoff
        ]
        for exchange_id in expired:
            del self._token_exchange_completed[exchange_id]

    def _settle_token_exchange(
        self, exchange_id: str, owned: Future[_TokenExchangeOutcome], outcome: _TokenExchangeOutcome
    ) -> None:
        self._token_exchange_in_flight.pop(exchange_id, None)
        if not owned.done():
            owned.set_result(outcome)

    def _stamp_completed_token_exchange(
        self, ctx: ActivityContext[SignInTokenExchangeInvokeActivity], exchange_id: str
    ) -> None:
        """Copy the completed marker into a deduplicated request's own turn state.

        Each turn loads its own state snapshot, and saves are last-write-wins with no
        compare-and-set. A duplicate whose snapshot predates the owner's write would
        otherwise erase that freshly persisted marker when its own save lands last.
        Only the in-memory marker is left alone here, so the TTL stays anchored to the
        moment the token was actually redeemed rather than being extended by every
        duplicate that arrives.

        Best-effort like every other persisted-marker touch: a state failure must not
        turn a successful duplicate into a failed invoke response.
        """
        try:
            if not has_completed_token_exchange(ctx.state, exchange_id):
                record_completed_token_exchange(ctx.state, exchange_id)
        except Exception:
            logger.exception("Unable to stamp completed OAuth token exchange into turn state.")

    def _replay_completed_token_exchange(
        self, ctx: ActivityContext[SignInTokenExchangeInvokeActivity], exchange_id: str
    ) -> TokenExchangeResult:
        """Answer a duplicate that arrived after its exchange already completed."""
        logger.debug("Duplicate signin/tokenExchange with id '%s' - returning 200 no-op.", exchange_id)
        self._stamp_completed_token_exchange(ctx, exchange_id)
        connection_name = self._resolved_connection_name(ctx.activity.value.connection_name)
        started_at = perf_counter()
        try:
            with get_tracer().start_as_current_span(
                APP_SPAN_NAMES.oauth_token_exchange,
                record_exception=False,
                set_status_on_exception=False,
            ) as span:
                span.set_attribute(APP_ATTRIBUTE_NAMES.oauth_connection, connection_name)
                span.set_attribute(APP_ATTRIBUTE_NAMES.oauth_operation, APP_OAUTH_OPERATIONS.token_exchange)
                span.set_attribute(APP_ATTRIBUTE_NAMES.oauth_result, APP_OAUTH_RESULTS.duplicate)
                span.set_attribute(APP_ATTRIBUTE_NAMES.invoke_response_status, 200)
                return InvokeResponse(status=200)
        finally:
            record_oauth_operation(
                connection_name,
                APP_OAUTH_OPERATIONS.token_exchange,
                APP_OAUTH_RESULTS.duplicate,
                (perf_counter() - started_at) * 1000,
            )

    async def _await_token_exchange(
        self,
        ctx: ActivityContext[SignInTokenExchangeInvokeActivity],
        exchange_id: str,
        in_flight: Future[_TokenExchangeOutcome],
    ) -> TokenExchangeResult:
        """Answer a duplicate that arrived while its exchange is still running.

        The waiter mirrors whatever the owning request produced, so a caller that lost
        the race still learns that the exchange failed (``412``) instead of being told
        the sign-in succeeded. It mirrors the owner's *result*, never its exception
        object -- see the failure branch below.
        """
        connection_name = self._resolved_connection_name(ctx.activity.value.connection_name)
        result = APP_OAUTH_RESULTS.duplicate
        started_at = perf_counter()
        try:
            with get_tracer().start_as_current_span(
                APP_SPAN_NAMES.oauth_token_exchange,
                record_exception=False,
                set_status_on_exception=False,
            ) as span:
                span.set_attribute(APP_ATTRIBUTE_NAMES.oauth_connection, connection_name)
                span.set_attribute(APP_ATTRIBUTE_NAMES.oauth_operation, APP_OAUTH_OPERATIONS.token_exchange)
                # Shielded: cancelling this waiter must not cancel the future the
                # owning request still has to resolve.
                outcome = await asyncio.shield(in_flight)
                # Stamped before the failure check: an exchange can fail after the
                # token was already spent, and the marker still has to survive this
                # request's own last-write-wins save.
                if outcome.token_redeemed:
                    self._stamp_completed_token_exchange(ctx, exchange_id)
                if outcome.error is not None:
                    result = APP_OAUTH_RESULTS.failure
                    span.set_attribute(APP_ATTRIBUTE_NAMES.oauth_result, result)
                    span.set_attribute(APP_ATTRIBUTE_NAMES.invoke_response_status, 412)
                    # Reported as a 412 rather than re-raised. Re-raising would hand
                    # this task an exception it never incurred: a ``CancelledError``
                    # from the owner would make an uncancelled waiter report itself as
                    # cancelled and trip ``except CancelledError`` cleanup, and one
                    # exception object shared between several waiters would have them
                    # all append frames to the same ``__traceback__``. Mirroring the
                    # result is what the TypeScript SDK does and what Teams needs.
                    return InvokeResponse(
                        status=412,
                        body=TokenExchangeInvokeResponse(
                            id=exchange_id,
                            connection_name=connection_name,
                            failure_detail=str(outcome.error) or "unable to exchange token...",
                        ),
                    )
                response = outcome.response
                # The owning request signals success by returning ``None``, which the
                # activity processor materializes as a 200. Duplicates say so
                # explicitly instead, matching the C# SDK's 200 no-op.
                status = response.status if isinstance(response, InvokeResponse) else 200
                span.set_attribute(APP_ATTRIBUTE_NAMES.oauth_result, result)
                span.set_attribute(APP_ATTRIBUTE_NAMES.invoke_response_status, status)
                return response if isinstance(response, InvokeResponse) else InvokeResponse(status=200)
        finally:
            record_oauth_operation(
                connection_name,
                APP_OAUTH_OPERATIONS.token_exchange,
                result,
                (perf_counter() - started_at) * 1000,
            )

    async def sign_in_failure(
        self, ctx: ActivityContext[SignInFailureInvokeActivity]
    ) -> Optional[InvokeResponse[None]]:
        """
        Default handler for signin/failure invoke activities.

        Teams sends a signin/failure invoke when SSO token exchange fails
        (e.g., due to a misconfigured Entra app registration). This handler
        logs the failure details and emits an error event so developers are
        notified rather than having the failure silently swallowed.

        **Connection attribution.** A ``signin/failure`` callback does not carry a
        connection name, so the failed connection is recovered from the pending
        sign-in recorded when the flow started — durable state when state is
        enabled, otherwise a short-lived process-local cache. Three outcomes:

            - No flows registered (legacy mode): the default connection is the only
              connection there is, so it is reported as the failed one.
            - A pending sign-in resolves: that flow is reported, and only its
              failure handlers run.
            - Flows are registered but nothing resolves — most commonly because the
              callback reached a different process than the one that started the
              sign-in, and state is not enabled to bridge them. The failed
              connection is genuinely unknown, so the global
              ``SignInFailureEvent.connection_name`` is ``None`` and telemetry omits
              the connection attribute rather than blaming the default. As a
              last resort **every** registered flow's failure handlers are notified,
              each with its own connection name, so no listener silently misses a
              failure that may have been theirs. Enable state to make attribution
              reliable across processes.

        Known failure codes (sent by the Teams client):
            - ``installappfailed``: Failed to install the app in the user's personal
              scope (non-silent).
            - ``authrequestfailed``: The SSO auth request failed after app installation
              (non-silent).
            - ``installedappnotfound``: The bot app is not installed for the user or group chat.
            - ``invokeerror``: A generic error occurred during the SSO invoke flow.
            - ``resourcematchfailed``: The token exchange resource URI on the OAuthCard does
              not match the Application ID URI in the Entra app registration's
              "Expose an API" section.
            - ``oauthcardnotvalid``: The bot's OAuthCard could not be parsed.
            - ``tokenmissing``: AAD token acquisition failed.
            - ``userconsentrequired``: The user needs to consent (handled via OAuth card
              fallback, does not typically reach the bot).
            - ``interactionrequired``: User interaction is required (handled via OAuth card
              fallback, does not typically reach the bot).
        """
        activity = ctx.activity
        next_handler = ctx.next
        pending_flows = self.oauth_registry._pending_flows(  # pyright: ignore[reportPrivateUsage]
            ctx, sso_only=True
        )
        target_flow = pending_flows[0] if pending_flows else None
        registered_flows = list(self.oauth_registry.values())
        if target_flow is not None:
            connection_name = target_flow.connection_name
        elif registered_flows:
            # Registered flows exist but nothing attributed this callback, so the
            # failed connection is genuinely unknown. Naming the default here would
            # blame a connection that may not have been involved at all.
            connection_name = None
        else:
            # Legacy mode: the default connection is the only one there is.
            connection_name = self.default_connection_name
        result = APP_OAUTH_RESULTS.notified
        started_at = perf_counter()
        try:
            with get_tracer().start_as_current_span(
                APP_SPAN_NAMES.oauth_signin_failure,
                record_exception=False,
                set_status_on_exception=False,
            ) as span:
                if connection_name is not None:
                    span.set_attribute(APP_ATTRIBUTE_NAMES.oauth_connection, connection_name)
                span.set_attribute(APP_ATTRIBUTE_NAMES.oauth_operation, APP_OAUTH_OPERATIONS.signin_failure)
                failure = activity.value
                if failure.code:
                    span.set_attribute(APP_ATTRIBUTE_NAMES.oauth_failure_code, failure.code)
                ctx.logger.warning(
                    f"Sign-in failed for user {activity.from_.id} in "
                    f"conversation {activity.conversation.id}: "
                    f"{failure.code} — {failure.message}. "
                    f"If the code is 'resourcematchfailed', verify that your Entra app "
                    f"registration has 'Expose an API' configured with the correct "
                    f"Application ID URI matching your OAuth connection's Token Exchange URL."
                )
                if target_flow is not None:
                    self.oauth_registry._mark_sso_consumed(  # pyright: ignore[reportPrivateUsage]
                        ctx, target_flow.connection_name
                    )
                await self.event_emitter.emit_async(
                    "error",
                    ErrorEvent(
                        error=Exception(f"Sign-in failure: {failure.code} — {failure.message}"),
                        context={"activity": activity},
                    ),
                )
                event = SignInFailureEvent(
                    activity_ctx=ctx,
                    connection_name=connection_name,
                    code=failure.code,
                    message=failure.message,
                )
                await self.event_emitter.emit_async("sign_in_failure", event)
                span.set_attribute(APP_ATTRIBUTE_NAMES.oauth_callback_invoked, True)
                span.set_attribute(APP_ATTRIBUTE_NAMES.oauth_result, result)
                callback_flows = [target_flow] if target_flow is not None else registered_flows
                for flow in callback_flows:
                    flow_event = (
                        event
                        if target_flow is not None
                        else SignInFailureEvent(
                            activity_ctx=ctx,
                            connection_name=flow.connection_name,
                            code=failure.code,
                            message=failure.message,
                        )
                    )
                    await flow._invoke_signin_failure_handlers(  # pyright: ignore[reportPrivateUsage]
                        flow_event
                    )
                return None
        finally:
            record_oauth_operation(
                connection_name,
                APP_OAUTH_OPERATIONS.signin_failure,
                result,
                (perf_counter() - started_at) * 1000,
            )
            await next_handler()

    async def sign_in_verify_state(
        self, ctx: ActivityContext[SignInVerifyStateInvokeActivity]
    ) -> Optional[InvokeResponse[None]]:
        """
        Decorator to register a function that handles the sign-in token exchange.
        """
        activity = ctx.activity
        api = ctx.api
        next_handler = ctx.next
        pending_flows = self.oauth_registry._pending_flows(ctx)  # pyright: ignore[reportPrivateUsage]
        candidates: list[tuple[str, Optional[OAuthFlow]]] = []
        seen_connections: set[str] = set()
        for flow in [*pending_flows, *self.oauth_registry.values()]:
            key = connection_lookup_key(flow.connection_name)
            if key is None or key in seen_connections:
                continue
            seen_connections.add(key)
            candidates.append((flow.connection_name, flow))

        default_flow = self.oauth_registry.get(self.default_connection_name)
        default_connection_name = (
            default_flow.connection_name if default_flow is not None else self.default_connection_name
        )
        if connection_lookup_key(default_connection_name) not in seen_connections:
            candidates.append((default_connection_name, default_flow))

        connection_name = candidates[0][0]
        if len(candidates) > 1:
            # ``signin/verifyState`` carries no connection name, so unhinted callbacks are
            # resolved by probing the Token Service once per candidate until one returns a
            # token. Hinted flows come first, so the normal path costs a single call; the
            # fan-out below is the fallback for missing/stale hints (state disabled, expired
            # sign-in, restarted storage). It is intentionally uncapped: dropping candidates
            # would turn a slow sign-in into a silently failed one.
            logger.debug(
                "Probing %d OAuth connection(s) for connection-less verify-state callback: %s",
                len(candidates),
                ", ".join(name for name, _ in candidates),
            )
        result = APP_OAUTH_RESULTS.failure
        started_at = perf_counter()
        try:
            with get_tracer().start_as_current_span(
                APP_SPAN_NAMES.oauth_verify_state,
                record_exception=False,
                set_status_on_exception=False,
            ) as span:
                span.set_attribute(APP_ATTRIBUTE_NAMES.oauth_connection, connection_name)
                span.set_attribute(APP_ATTRIBUTE_NAMES.oauth_operation, APP_OAUTH_OPERATIONS.verify_state)

                if not activity.value.state:
                    logger.warning(
                        f"Auth state not present for conversation id '{activity.conversation.id}' "
                        f"and user id '{activity.from_.id}'. "
                    )
                    result = APP_OAUTH_RESULTS.no_token
                    span.set_attribute(APP_ATTRIBUTE_NAMES.invoke_response_status, 404)
                    span.set_attribute(APP_ATTRIBUTE_NAMES.oauth_result, result)
                    return InvokeResponse(status=404)

                logger.debug(
                    f"Verifying sign-in state for user {activity.from_.id} in conversation"
                    f"{activity.conversation.id} with state {activity.value.state}"
                )

                for candidate_connection_name, flow in candidates:
                    # Deliberately rebind the outer name: the ``finally`` block below records
                    # telemetry against the connection that was probed last, which is the one
                    # the outcome (success, 412, or exhausted candidates) actually belongs to.
                    connection_name = candidate_connection_name
                    span.set_attribute(APP_ATTRIBUTE_NAMES.oauth_connection, connection_name)
                    try:
                        token = await api.users.get_token(
                            GetUserTokenParams(
                                connection_name=connection_name,
                                user_id=activity.from_.id,
                                channel_id=activity.channel_id,
                                code=activity.value.state,
                            )
                        )
                    except HTTPStatusError as e:
                        status = e.response.status_code
                        if status in (400, 404, 412):
                            # An expected miss. ``signin/verifyState`` carries no
                            # connection name, so the Token Service rejecting this
                            # code only rules out this candidate - it is not a failed
                            # sign-in until every candidate has been ruled out.
                            logger.debug(
                                f"OAuth connection '{connection_name}' did not accept the verify-state code "
                                f"for user {activity.from_.id} in conversation "
                                f"{activity.conversation.id} (HTTP {status})."
                            )
                            continue
                        logger.error(
                            f"Error verifying sign-in state for user {activity.from_.id} in conversation"
                            f"{activity.conversation.id}: {e}"
                        )
                        await self.event_emitter.emit_async(
                            "error",
                            ErrorEvent(error=e, context={"activity": activity}),
                        )
                        error_type = APP_OAUTH_ERROR_TYPES.http_error
                        span.set_attribute(APP_ATTRIBUTE_NAMES.oauth_error_type, error_type)
                        record_exception(span, e)
                        record_oauth_error(connection_name, APP_OAUTH_OPERATIONS.verify_state, error_type)
                        status = status or 500
                        span.set_attribute(APP_ATTRIBUTE_NAMES.invoke_response_status, status)
                        span.set_attribute(APP_ATTRIBUTE_NAMES.oauth_result, result)
                        return InvokeResponse(status=status)
                    except Exception as e:
                        # A transport fault or a bug, not a Token Service verdict.
                        # It propagates so the app's error handling reports it once
                        # rather than being flattened into a 412 that reads as an
                        # ordinary failed sign-in.
                        logger.error(
                            f"Error verifying sign-in state for user {activity.from_.id} in conversation"
                            f"{activity.conversation.id}: {e}"
                        )
                        error_type = APP_OAUTH_ERROR_TYPES.exception
                        span.set_attribute(APP_ATTRIBUTE_NAMES.oauth_error_type, error_type)
                        record_exception(span, e)
                        record_oauth_error(connection_name, APP_OAUTH_OPERATIONS.verify_state, error_type)
                        result = APP_OAUTH_RESULTS.failure
                        span.set_attribute(APP_ATTRIBUTE_NAMES.oauth_result, result)
                        raise

                    ctx.is_signed_in = True
                    ctx.user_token = token.token
                    self.oauth_registry._clear_pending(  # pyright: ignore[reportPrivateUsage]
                        ctx, connection_name
                    )
                    event = SignInEvent(
                        activity_ctx=ctx,
                        token_response=token,
                        connection_name=connection_name,
                    )
                    result = APP_OAUTH_RESULTS.success
                    span.set_attribute(APP_ATTRIBUTE_NAMES.oauth_callback_invoked, True)
                    span.set_attribute(APP_ATTRIBUTE_NAMES.oauth_result, result)
                    await self.event_emitter.emit_async("sign_in", event)
                    if flow is not None:
                        await flow._invoke_signin_handlers(  # pyright: ignore[reportPrivateUsage]
                            event
                        )
                    logger.debug(
                        f"Sign-in state verified for user {activity.from_.id} in conversation "
                        f"{activity.conversation.id}"
                    )
                    return None

                # Every candidate missed, so the user holds no token on any of them.
                # That is "nothing to verify" (404), not a precondition failure.
                result = APP_OAUTH_RESULTS.no_token
                span.set_attribute(APP_ATTRIBUTE_NAMES.invoke_response_status, 404)
                span.set_attribute(APP_ATTRIBUTE_NAMES.oauth_result, result)
                return InvokeResponse(status=404)
        finally:
            record_oauth_operation(
                connection_name,
                APP_OAUTH_OPERATIONS.verify_state,
                result,
                (perf_counter() - started_at) * 1000,
            )
            await next_handler()
