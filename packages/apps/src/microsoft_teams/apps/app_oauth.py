"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import logging
from time import perf_counter
from typing import Optional, Union

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
from .routing import ActivityContext

logger = logging.getLogger(__name__)


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

    async def sign_in_token_exchange(
        self, ctx: ActivityContext[SignInTokenExchangeInvokeActivity]
    ) -> Union[TokenExchangeInvokeResponseType, InvokeResponse[TokenExchangeInvokeResponseType]]:
        """
        Decorator to register a function that handles the sign-in token exchange.
        """
        activity = ctx.activity
        api = ctx.api
        next_handler = ctx.next
        connection_name = activity.value.connection_name
        result = APP_OAUTH_RESULTS.failure
        started_at = perf_counter()
        try:
            with get_tracer().start_as_current_span(
                APP_SPAN_NAMES.oauth_token_exchange,
                record_exception=False,
                set_status_on_exception=False,
            ) as span:
                span.set_attribute(APP_ATTRIBUTE_NAMES.oauth_connection, connection_name)
                span.set_attribute(APP_ATTRIBUTE_NAMES.oauth_operation, APP_OAUTH_OPERATIONS.token_exchange)

                flow = self.oauth_registry.get(connection_name)
                event_connection_name = flow.connection_name if flow is not None else connection_name

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
                        record_oauth_error(connection_name, APP_OAUTH_OPERATIONS.token_exchange, error_type)
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
                    record_oauth_error(connection_name, APP_OAUTH_OPERATIONS.token_exchange, error_type)
                    result = APP_OAUTH_RESULTS.failure
                    span.set_attribute(APP_ATTRIBUTE_NAMES.oauth_result, result)
                    raise

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
                connection_name,
                APP_OAUTH_OPERATIONS.token_exchange,
                result,
                (perf_counter() - started_at) * 1000,
            )
            await next_handler()

    async def sign_in_failure(
        self, ctx: ActivityContext[SignInFailureInvokeActivity]
    ) -> Optional[InvokeResponse[None]]:
        """
        Default handler for signin/failure invoke activities.

        Teams sends a signin/failure invoke when SSO token exchange fails
        (e.g., due to a misconfigured Entra app registration). This handler
        logs the failure details and emits an error event so developers are
        notified rather than having the failure silently swallowed.

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
        connection_name = target_flow.connection_name if target_flow is not None else self.default_connection_name
        result = APP_OAUTH_RESULTS.notified
        started_at = perf_counter()
        try:
            with get_tracer().start_as_current_span(
                APP_SPAN_NAMES.oauth_signin_failure,
                record_exception=False,
                set_status_on_exception=False,
            ) as span:
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
                callback_flows = [target_flow] if target_flow is not None else list(self.oauth_registry.values())
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
