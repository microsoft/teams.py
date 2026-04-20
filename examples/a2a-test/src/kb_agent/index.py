"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import os
from dataclasses import dataclass
from typing import Any, cast

from azure.core.exceptions import ResourceNotFoundError
from azure.identity.aio import ClientSecretCredential
from azure.search.documents.aio import SearchClient
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(usecwd=True))


@dataclass
class KBDoc:
    id: str
    title: str
    source: str
    content: str

    @property
    def snippet(self) -> str:
        body = self.content.split("\n", 1)[1].strip() if "\n" in self.content else self.content
        return body[:240].strip()


def _to_doc(r: dict[str, Any]) -> KBDoc:
    return KBDoc(id=r["id"], title=r["title"], source=r["source"], content=r["content"])


class KBIndex:
    """Thin wrapper around an Azure AI Search index holding the Northwind KB corpus."""

    def __init__(self) -> None:
        self._client = SearchClient(
            endpoint=os.environ["AZURE_SEARCH_ENDPOINT"],
            index_name=os.environ["AZURE_SEARCH_INDEX_NAME"],
            credential=ClientSecretCredential(
                tenant_id=os.environ["TENANT_ID"],
                client_id=os.environ["CLIENT_ID"],
                client_secret=os.environ["CLIENT_SECRET"],
            ),
        )

    async def search(self, query: str, k: int = 3) -> list[KBDoc]:
        results = await self._client.search(search_text=query, top=k)
        return [_to_doc(cast(dict[str, Any], r)) async for r in results]

    async def get(self, doc_id: str) -> KBDoc | None:
        try:
            r = await self._client.get_document(key=doc_id)
            return _to_doc(cast(dict[str, Any], r))
        except ResourceNotFoundError:
            return None
