"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import cast
from uuid import uuid4

import jwt
from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse
from microsoft.teams.api import Account, Activity, ConversationAccount, JsonWebToken, MessageActivity

from ....context import RouteContext


async def create(context: RouteContext):
    async def create_activity_endpoint(request: Request, response: Response):
        is_client = request.headers.get("x-teams-devtools") == "true"
        body = await request.json()
        channel_data = body.get("channelData", {})
        id = channel_data.get("streamId", str(uuid4()))

        if not is_client:
            response = JSONResponse(status_code=201, content={"id": id})
            return response

        try:
            token = JsonWebToken(
                jwt.encode({"serviceurl": f"http://localhost:{context.port}"}, "secret", algorithm="HS256")
            )

            activity = MessageActivity(
                **body,
                id=body.get("id", str(uuid4())),
                channel_id="msteams",
                from_=Account(id="devtools", name="devtools", role="bot"),
                recipient=Account(id="", name="", role="user"),
                conversation=ConversationAccount(
                    id=request.path_params["conversationId"],
                    conversation_type="personal",
                    is_group=False,
                    name="default",
                ),
            )

            cast_activity = cast(Activity, activity)
            await context.process(token, cast_activity)
            response = JSONResponse(status_code=201, content={"id": id})
            return response

        except Exception as err:
            context.log.error(err)
            raise HTTPException(status_code=500, detail=str(err)) from err

    return create_activity_endpoint
