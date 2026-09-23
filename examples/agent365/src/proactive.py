"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import argparse
import asyncio
import logging

from microsoft.opentelemetry.a365.core import AgentDetails, InvokeAgentScope, InvokeAgentScopeDetails, Request
from microsoft_teams.api import MessageActivityInput
from microsoft_teams.apps import Agent365ScopeOptions, App, create_agent365_scope
from observability import Agent365TokenCache, flush_agent365_spans, use_agent365_exporter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

agent365: Agent365ScopeOptions = {
    "include": ["agentName", "agentEmail"],
    "operation_source": "Microsoft.Teams.Apps",
    "channel_name": "msteams",
}
open_agent365_scope = create_agent365_scope(agent365)


async def main():
    parser = argparse.ArgumentParser(description="Send proactive messages using AgenticIdentity scoping")
    parser.add_argument("conversation_id", help="The Teams conversation ID to send messages to")
    parser.add_argument("agentic_app_id", help="The AgenticIdentity app/client ID")
    parser.add_argument("agentic_user_id", help="The agentic user object ID")
    args = parser.parse_args()

    app = App(telemetry={"agent365": agent365})
    token_cache = Agent365TokenCache()
    use_agent365_exporter(token_cache)
    try:
        await app.initialize()

        agentic_identity = app.get_agentic_identity(args.agentic_app_id, args.agentic_user_id)
        if agentic_identity.tenant_id is None:
            raise RuntimeError("TENANT_ID is required for Agent365 observability")
        await token_cache.refresh(
            app.token_provider,
            args.agentic_app_id,
            agentic_identity.tenant_id,
        )

        with open_agent365_scope(
            agentic_identity=agentic_identity,
            conversation_id=args.conversation_id,
        ):
            with InvokeAgentScope.start(
                Request(conversation_id=args.conversation_id),
                InvokeAgentScopeDetails(),
                AgentDetails(
                    agent_id=args.agentic_app_id,
                    agentic_user_id=agentic_identity.agentic_user_id,
                    agent_blueprint_id=agentic_identity.agentic_app_blueprint_id,
                    tenant_id=agentic_identity.tenant_id,
                ),
            ):
                sent = await app.send(
                    args.conversation_id,
                    "Hello from app.send with an AgenticIdentity.",
                    agentic_identity=agentic_identity,
                )
                logger.info("Sent activity through app.send. Activity ID: %s", sent.id)

                api_sent = await app.api.for_agentic_identity(agentic_identity).conversations.create_activity(
                    args.conversation_id,
                    MessageActivityInput(text="Hello from the conversation activity API with an AgenticIdentity."),
                )
                logger.info("Sent activity through app.api. Activity ID: %s", api_sent.id)
    finally:
        flush_agent365_spans()


if __name__ == "__main__":
    asyncio.run(main())
