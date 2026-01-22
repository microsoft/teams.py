"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio

from microsoft_teams.api.activities.event import (
    MeetingEndEventActivity,
    MeetingParticipantJoinEventActivity,
    MeetingParticipantLeaveEventActivity,
    MeetingStartEventActivity,
)
from microsoft_teams.api.activities.message import MessageActivity
from microsoft_teams.api.activities.typing import TypingActivityInput
from microsoft_teams.apps import ActivityContext, App
from microsoft_teams.cards import AdaptiveCard, OpenUrlAction, TextBlock

app = App()


@app.on_meeting_start
async def handle_meeting_start(ctx: ActivityContext[MeetingStartEventActivity]):
    meeting_data = ctx.activity.value
    start_time = meeting_data.StartTime.strftime("%c")

    card = AdaptiveCard(
        body=[
            TextBlock(
                text=f"'{meeting_data.Title}' has started at {start_time}.",
                wrap=True,
                weight="Bolder",
            )
        ],
        actions=[OpenUrlAction(url=meeting_data.JoinUrl, title="Join the meeting")],
    )

    await ctx.send(card)


@app.on_meeting_end
async def handle_meeting_end(ctx: ActivityContext[MeetingEndEventActivity]):
    meeting_data = ctx.activity.value
    end_time = meeting_data.EndTime.strftime("%c")

    card = AdaptiveCard(
        body=[
            TextBlock(
                text=f"'{meeting_data.Title}' has ended at {end_time}.",
                wrap=True,
                weight="Bolder",
            )
        ]
    )

    await ctx.send(card)


@app.on_meeting_participant_join
async def handle_meeting_participant_join(ctx: ActivityContext[MeetingParticipantJoinEventActivity]):
    meeting_data = ctx.activity.value
    member = meeting_data.members[0].user.name
    role = meeting_data.members[0].meeting.role

    card = AdaptiveCard(
        body=[
            TextBlock(
                text=f"{member} has joined the meeting as {role}.",
                wrap=True,
                weight="Bolder",
            )
        ]
    )

    await ctx.send(card)


@app.on_meeting_participant_leave
async def handle_meeting_participant_leave(ctx: ActivityContext[MeetingParticipantLeaveEventActivity]):
    meeting_data = ctx.activity.value
    member = meeting_data.members[0].user.name

    card = AdaptiveCard(
        body=[
            TextBlock(
                text=f"{member} has left the meeting.",
                wrap=True,
                weight="Bolder",
            )
        ]
    )

    await ctx.send(card)


@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]):
    await ctx.reply(TypingActivityInput())
    await ctx.send(f'you said "{ctx.activity.text}"')


if __name__ == "__main__":
    asyncio.run(app.start())
