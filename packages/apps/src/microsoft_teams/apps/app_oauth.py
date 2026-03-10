"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import logging
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

from .events import ErrorEvent, EventType, SignInEvent
from .routing import ActivityContext

logger = logging.getLogger(__name__)


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
        activity = ctx.activity
        api = ctx.api
        next_handler = ctx.next
        try:
            if activity.value.connection_name != self.default_connection_name:
                logger.warning(
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
                if isinstance(e, HTTPStatusError):
                    status = e.response.status_code
                    if status not in (404, 400, 412):
                        logger.error(
                            f"Error exchanging token for user {activity.from_.id} in "
                            f"conversation {activity.conversation.id}: {e}"
                        )
                        self.event_emitter.emit("error", ErrorEvent(error=e, context={"activity": activity}))
                        return InvokeResponse(status=status or 500)
                    logger.info(
                        f"Unable to exchange token for user {activity.from_.id} in "
                        f"conversation {activity.conversation.id}: {e}"
                    )
                else:
                    logger.error(
                        f"Unable to exchange token for user {activity.from_.id} in "
                        f"conversation {activity.conversation.id}: {e}"
                    )
                    self.event_emitter.emit("error", ErrorEvent(error=e, context={"activity": activity}))
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
        try:
            failure = activity.value
            ctx.logger.warning(
                f"Sign-in failed for user {activity.from_.id} in "
                f"conversation {activity.conversation.id}: "
                f"{failure.code} — {failure.message}. "
                f"If the code is 'resourcematchfailed', verify that your Entra app "
                f"registration has 'Expose an API' configured with the correct "
                f"Application ID URI matching your OAuth connection's Token Exchange URL."
            )
            self.event_emitter.emit(
                "error",
                ErrorEvent(
                    error=Exception(f"Sign-in failure: {failure.code} — {failure.message}"),
                    context={"activity": activity},
                ),
            )
            return None
        finally:
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
        try:
            if not activity.value.state:
                logger.warning(
                    f"Auth state not present for conversation id '{activity.conversation.id}' "
                    f"and user id '{activity.from_.id}'. "
                )
                return InvokeResponse(status=404)

            logger.debug(
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
                logger.debug(
                    f"Sign-in state verified for user {activity.from_.id} in conversation {activity.conversation.id}"
                )
                return None
            except Exception as e:
                logger.error(
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
