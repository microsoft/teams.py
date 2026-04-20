"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import os
import re
from pathlib import Path
from typing import Any

from azure.core.exceptions import ResourceNotFoundError
from azure.identity import ClientSecretCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchableField,
    SearchFieldDataType,
    SearchIndex,
    SimpleField,
)
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(usecwd=True))

_KB_ROOT = Path(__file__).parent / "knowledge_base"
_SECTION_SPLIT = re.compile(r"(?=^## )", flags=re.MULTILINE)


def _load_chunks(root: Path) -> list[dict[str, Any]]:
    """Walk the markdown docs, split by ## sections, produce upload-ready records."""
    out: list[dict[str, Any]] = []
    for path in sorted(root.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        for i, section in enumerate(_SECTION_SPLIT.split(text)):
            section = section.strip()
            if not section:
                continue
            first_line = section.split("\n", 1)[0].strip()
            title = first_line.lstrip("#").strip() or path.stem
            out.append(
                {
                    "id": f"{path.stem}-{i}",  # Azure Search keys disallow '#'
                    "title": title,
                    "source": path.name,
                    "content": section,
                }
            )
    return out


def _ensure_index(endpoint: str, credential: ClientSecretCredential, index_name: str) -> None:
    client = SearchIndexClient(endpoint=endpoint, credential=credential)
    try:
        client.get_index(index_name)
        print(f"Index '{index_name}' already exists — reusing.")
        return
    except ResourceNotFoundError:
        pass
    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SearchableField(name="title", type=SearchFieldDataType.String),
        SimpleField(name="source", type=SearchFieldDataType.String, filterable=True),
        SearchableField(name="content", type=SearchFieldDataType.String),
    ]
    client.create_index(SearchIndex(name=index_name, fields=fields))
    print(f"Created index '{index_name}'.")


def main() -> None:
    endpoint = os.environ["AZURE_SEARCH_ENDPOINT"]
    index_name = os.environ["AZURE_SEARCH_INDEX_NAME"]
    credential = ClientSecretCredential(
        tenant_id=os.environ["AZURE_TENANT_ID"],
        client_id=os.environ["AZURE_CLIENT_ID"],
        client_secret=os.environ["AZURE_CLIENT_SECRET"],
    )

    _ensure_index(endpoint, credential, index_name)

    client = SearchClient(endpoint=endpoint, index_name=index_name, credential=credential)
    chunks = _load_chunks(_KB_ROOT)
    result = client.upload_documents(chunks)
    succeeded = sum(1 for r in result if r.succeeded)
    print(f"Uploaded {succeeded}/{len(chunks)} chunks to '{index_name}'.")


if __name__ == "__main__":
    main()
