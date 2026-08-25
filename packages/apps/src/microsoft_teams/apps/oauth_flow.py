"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import logging
from collections import OrderedDict
from dataclasses import replace
from typing import Any, Awaitable, Callable, Iterator, List, Mapping, Optional

from .events import SignInEvent, SignInFailureEvent
from .routing import ActivityContext, SignInOptions

logger = logging.getLogger(__name__)

SignInHandler = Callable[[SignInEvent], Awaitable[None]]
SignInFailureHandler = Callable[[SignInFailureEvent], Awaitable[None]]

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
        self.connection_name = connection_name
        self._defaults = SignInOptions(
            oauth_card_text=oauth_card_text,
            sign_in_button_text=sign_in_button_text,
            connection_name=connection_name,
        )
        self._on_signin: List[SignInHandler] = []
        self._on_signin_failure: List[SignInFailureHandler] = []

    def __repr__(self) -> str:
        return f"OAuthFlow(connection_name={self.connection_name!r})"

    # -- handler registration -------------------------------------------------

    def on_signin(self, func: SignInHandler) -> SignInHandler:
        """Register a handler for a successful sign-in on this connection."""
        self._on_signin.append(func)
        return func

    def on_signin_failure(self, func: SignInFailureHandler) -> SignInFailureHandler:
        """Register a handler for a failed silent-SSO attempt on this connection."""
        self._on_signin_failure.append(func)
        return func

    # -- operations -----------------------------------------------------------

    async def sign_in(self, ctx: ActivityContext[Any], options: Optional[SignInOptions] = None) -> Optional[str]:
        """Start sign-in.

        Returns a token immediately if one already exists, otherwise sends an
        OAuth card and returns ``None``. If the caller passes their own
        ``SignInOptions`` their card text wins, but the connection name is
        always forced to this flow's — you cannot accidentally sign in on the
        wrong connection through a flow object.
        """
        base = self._defaults if options is None else options
        return await ctx.sign_in(replace(base, connection_name=self.connection_name))

    async def sign_out(self, ctx: ActivityContext[Any]) -> None:
        """Sign the user out of this connection."""
        await ctx.sign_out(connection_name=self.connection_name)

    async def get_token(self, ctx: ActivityContext[Any]) -> Optional[str]:
        """The user's token for this connection, or ``None`` if not signed in."""
        return await ctx.get_user_token(connection_name=self.connection_name)

    async def is_signed_in(self, ctx: ActivityContext[Any]) -> bool:
        """Whether the user currently has a token for this connection."""
        return await ctx.get_user_token(connection_name=self.connection_name) is not None


class OAuthFlowRegistry(Mapping[str, OAuthFlow]):
    """Case-insensitive, insertion-ordered collection of ``OAuthFlow``.

    Subclasses ``Mapping``, so ``in``, ``.get()``, ``.values()``, ``len()`` and
    truthiness all work without extra code.
    """

    def __init__(self) -> None:
        self._flows: "OrderedDict[str, OAuthFlow]" = OrderedDict()

    def __getitem__(self, connection_name: str) -> OAuthFlow:
        return self._flows[connection_name.lower()]

    def __iter__(self) -> Iterator[str]:
        return (flow.connection_name for flow in self._flows.values())

    def __len__(self) -> int:
        return len(self._flows)

    def add(self, flow: OAuthFlow) -> OAuthFlow:
        """Register a flow. Raises ``ValueError`` if the connection already exists."""
        key = flow.connection_name.lower()
        if key in self._flows:
            raise ValueError(
                f"An OAuth flow for connection '{flow.connection_name}' is already "
                f"registered. Connection names are case-insensitive."
            )
        self._flows[key] = flow
        return flow
