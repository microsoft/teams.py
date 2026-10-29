"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import logging
import re

from microsoft_teams.api import (
    CitationIconName,
    MessageActivity,
    MessageActivityInput,
    PlanInfoEntity,
    Step,
    StepSource,
)
from microsoft_teams.apps import ActivityContext, App, Plan, PlanOptions

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
app = App()
proactive_tasks: set[asyncio.Task[None]] = set()


def _command(name: str) -> re.Pattern[str]:
    mention = r"(?:<at\b[^>]*>.*?</at>|@\S+)"
    return re.compile(
        rf"\s*(?:{mention}\s*)*{re.escape(name)}[ \t]*(?:\r?\n[\s\S]*)?$",
        re.IGNORECASE | re.DOTALL,
    )


def create_lookup_step() -> Step:
    return Step(
        id="lookup",
        version=1,
        status="active",
        title="Checking sources",
        description="Looking for relevant information in the Teams SDK documentation.",
    )


async def prepare_answer(plan: Plan, ready_description: str) -> None:
    await plan.start(
        [
            create_lookup_step(),
            Step(
                id="answer",
                # NOTE: Any update to this step requires incrementing this version number.
                version=1,
                status="proposed",
                title="Draft answer",
                description="Summarize the findings once the sources have been checked.",
            ),
        ]
    )
    await asyncio.sleep(2)
    await plan.update(
        [
            Step(
                id="lookup",
                version=2,
                status="blocked",
                title="Waiting for source response",
                description="The source has not responded yet; waiting before continuing.",
            )
        ]
    )
    await asyncio.sleep(2)
    await plan.update(
        [
            Step(
                id="lookup",
                version=3,
                status="completed",
                title="Sources checked",
                description="Found the relevant Teams SDK documentation for the answer.",
                sources=[
                    StepSource(
                        title="Teams SDK docs",
                        url="https://microsoft.github.io/teams-sdk/",
                        icon=CitationIconName.TEXT,
                    )
                ],
            ),
            Step(
                id="answer",
                version=2,
                status="active",
                title="Drafting answer",
                description="Turning the source information into a concise response.",
            ),
        ]
    )
    await asyncio.sleep(2)
    await plan.update(
        [
            Step(
                id="answer",
                version=3,
                status="completed",
                title="Answer ready",
                description=ready_description,
            )
        ]
    )
    await asyncio.sleep(2)


@app.on_message_pattern(_command("complete"))
async def handle_complete(ctx: ActivityContext[MessageActivity]) -> None:
    plan = ctx.plan()
    await prepare_answer(plan, "The response is ready to send.")
    await plan.complete("Here is the answer based on the sources.")


@app.on_message_pattern(_command("complete-stream"))
async def handle_complete_stream(ctx: ActivityContext[MessageActivity]) -> None:
    plan = ctx.plan()
    await prepare_answer(plan, "The response is ready to stream.")
    for chunk in ("Here is ", "the answer ", "based on the sources."):
        ctx.stream.emit(chunk)
        await asyncio.sleep(0.5)
    ctx.stream.emit(MessageActivityInput(entities=[PlanInfoEntity(plan_type="complete")]))
    await ctx.stream.close()


@app.on_message_pattern(_command("stop"))
async def handle_stop(ctx: ActivityContext[MessageActivity]) -> None:
    plan = ctx.plan()
    await plan.start([create_lookup_step()])
    await asyncio.sleep(5)
    await plan.stop()


@app.on_message_pattern(_command("error"))
async def handle_error(ctx: ActivityContext[MessageActivity]) -> None:
    plan = ctx.plan()
    await plan.start([create_lookup_step()])
    await asyncio.sleep(2)
    await plan.update(
        [
            Step(
                id="lookup",
                version=2,
                status="error",
                title="Source lookup failed",
                description="The source could not be retrieved, so the lookup cannot continue.",
            )
        ]
    )
    await asyncio.sleep(2)
    await plan.error()


async def send_proactive_plan(plan_options: PlanOptions) -> None:
    await asyncio.sleep(10)
    plan = Plan(**plan_options)
    await plan.update(
        [
            Step(
                id="report",
                version=2,
                status="completed",
                title="Report ready",
                description="The background work is complete and the report is ready to send.",
            ),
            Step(
                id="deliver",
                version=1,
                status="active",
                title="Delivering report",
                description="Finalizing delivery of the completed report back to the user.",
            ),
        ]
    )
    await asyncio.sleep(2)
    await plan.update(
        [
            Step(
                id="deliver",
                version=2,
                status="completed",
                title="Delivered report",
                description="Finalized delivery of the completed report back to the user.",
            ),
        ]
    )
    await asyncio.sleep(10)
    await plan.complete("Your background report is ready.")


def on_proactive_done(task: asyncio.Task[None]) -> None:
    proactive_tasks.discard(task)
    if not task.cancelled():
        error = task.exception()
        if error is not None:
            logger.error("Proactive Plan failed", exc_info=error)


@app.on_message_pattern(_command("proactive"))
async def handle_proactive(ctx: ActivityContext[MessageActivity]) -> None:
    plan = ctx.plan()
    await plan.start(
        [
            Step(
                id="report",
                version=1,
                status="active",
                title="Preparing background report",
                description="This report continues in the background after the handler returns.",
            )
        ]
    )

    # Saving the plan metadata for long-running tasks
    plan_options = PlanOptions(**plan.model_dump(mode="json", by_alias=False), api_client=ctx.api)
    task = asyncio.create_task(send_proactive_plan(plan_options))
    proactive_tasks.add(task)
    task.add_done_callback(on_proactive_done)


@app.on_message
async def handle_help(ctx: ActivityContext[MessageActivity]) -> None:
    await ctx.send("Send `complete`, `complete-stream`, `stop`, `error`, or `proactive` to run a Plan lifecycle demo.")


if __name__ == "__main__":
    asyncio.run(app.start())
