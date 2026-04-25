"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, TypeAdapter

# A2A message shapes exchanged between Alice and Bob. `kind` discriminates
# between an outbound question (`ask`) and the peer's answer (`reply`).


class AskMessage(BaseModel):
    kind: Literal["ask"] = "ask"
    qid: str
    question: str
    sender: str
    reply_url: str


class ReplyMessage(BaseModel):
    kind: Literal["reply"] = "reply"
    qid: str
    answer: str
    responder: str


A2AMessage = Annotated[Union[AskMessage, ReplyMessage], Field(discriminator="kind")]
A2AMessageAdapter: TypeAdapter[A2AMessage] = TypeAdapter(A2AMessage)
