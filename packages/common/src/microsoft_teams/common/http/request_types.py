"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from collections.abc import AsyncIterable, Iterable, Mapping, Sequence
from typing import IO, TypeAlias

import httpx2

# SDK-owned parameter types: HTTPX2 does not publicly export these aliases.
_QueryValue: TypeAlias = str | int | float | bool | None
QueryParamTypes: TypeAlias = (
    httpx2.QueryParams
    | Mapping[str, _QueryValue | Sequence[_QueryValue]]
    | list[tuple[str, _QueryValue]]
    | tuple[tuple[str, _QueryValue], ...]
    | str
    | bytes
)
RequestContent: TypeAlias = str | bytes | Iterable[bytes] | AsyncIterable[bytes]
RequestData: TypeAlias = Mapping[str, object]
_FileContent: TypeAlias = IO[bytes] | bytes | str
_FileValue: TypeAlias = (
    _FileContent
    | tuple[str | None, _FileContent]
    | tuple[str | None, _FileContent, str | None]
    | tuple[str | None, _FileContent, str | None, Mapping[str, str]]
)
RequestFiles: TypeAlias = Mapping[str, _FileValue] | Sequence[tuple[str, _FileValue]]
