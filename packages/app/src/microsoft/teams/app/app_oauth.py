"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional, Union

from httpx import HTTPStatusError
from microsoft.teams.api import (
    ExchangeUserTokenParams,
    GetUserTokenParams,
    InvokeResponse,
    SignInTokenExchangeInvokeActivity,
    SignInVerifyStateInvokeActivity,
    TokenExchangeInvokeResponse,
    TokenExchangeInvokeResponseType,
    TokenExchangeRequest,
)
from microsoft.teams.common import EventEmitter

from .events import ErrorEvent, EventType, SignInEvent
from .routing import ActivityContext


class OauthHandlers:
    def __init__(self, default_connection_name: str, event_emitter: EventEmitter[EventType]) -> None:
        self.default_connection_name = default_connection_name
        self.event_emitter = event_emitter

    async def sign_in_token_exchange(
        self, ctx: ActivityContext[SignInTokenExchangeInvokeActivity]
    ) -> Union[TokenExchangeInvokeResponseType, InvokeResponse[TokenExchangeInvokeResponseType]]:
        """
        Decorator to register a function that handles the sign-in token exchange.
        """
        log = ctx.logger
        activity = ctx.activity
        api = ctx.api
        next_handler = ctx.next
        try:
            if activity.value.connection_name != self.default_connection_name:
                log.warning(
                    f"Sign-in token exchange invoked with connection name '{activity.value.connection_name}', "
                    f"but default connection name is '{self.default_connection_name}'. "
                    f"Token verification will likely fail."
                )

            try:
                token = await api.users.token.exchange(
                    ExchangeUserTokenParams(
                        connection_name=activity.value.connection_name,
                        user_id=activity.from_.id,
                        channel_id=activity.channel_id,
                        exchange_request=TokenExchangeRequest(
                            token=activity.value.token,
                        ),
                    )
                )
                self.event_emitter.emit("sign_in", SignInEvent(activity_ctx=ctx, token_response=token))
                return None
            except Exception as e:
                ctx.logger.error(
                    f"Error exchanging token for user {activity.from_.id} in "
                    f"conversation {activity.conversation.id}: {e}"
                )
                if isinstance(e, HTTPStatusError):
                    status = e.response.status_code
                    if status not in (404, 400, 412):
                        self.event_emitter.emit("error", ErrorEvent(error=e, context={"activity": activity}))
                        return InvokeResponse(status=status or 500)
                ctx.logger.warning(
                    f"Unable to exchange token for user {activity.from_.id} in "
                    f"conversation {activity.conversation.id}: {e}"
                )
                return InvokeResponse(
                    status=412,
                    body=TokenExchangeInvokeResponse(
                        id=activity.value.id,
                        connection_name=activity.value.connection_name,
                        failure_detail=str(e) or "unable to exchange token...",
                    ),
                )
        finally:
            await next_handler()

    async def sign_in_verify_state(
        self, ctx: ActivityContext[SignInVerifyStateInvokeActivity]
    ) -> Optional[InvokeResponse[None]]:
        """
        Decorator to register a function that handles the sign-in token exchange.
        """
        log = ctx.logger
        activity = ctx.activity
        api = ctx.api
        next_handler = ctx.next
        try:
            if not activity.value.state:
                log.warning(
                    f"Auth state not present for conversation id '{activity.conversation.id}' "
                    f"and user id '{activity.from_.id}'. "
                )
                return InvokeResponse(status=404)

            log.debug(
                f"Verifying sign-in state for user {activity.from_.id} in conversation"
                f"{activity.conversation.id} with state {activity.value.state}"
            )

            try:
                token = await api.users.token.get(
                    GetUserTokenParams(
                        connection_name=self.default_connection_name,
                        user_id=activity.from_.id,
                        channel_id=activity.channel_id,
                        code=activity.value.state,
                    )
                )
                self.event_emitter.emit("sign_in", SignInEvent(activity_ctx=ctx, token_response=token))
                log.debug(
                    f"Sign-in state verified for user {activity.from_.id} in conversation {activity.conversation.id}"
                )
                return None
            except Exception as e:
                log.error(
                    f"Error verifying sign-in state for user {activity.from_.id} in conversation"
                    f"{activity.conversation.id}: {e}"
                )
                if isinstance(e, HTTPStatusError):
                    status = e.response.status_code
                    if status not in (404, 400, 412):
                        self.event_emitter.emit("error", ErrorEvent(error=e, context={"activity": activity}))
                        return InvokeResponse(status=status or 500)
                return InvokeResponse(
                    status=412,
                )
        finally:
            await next_handler()
