from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

import httpx


@runtime_checkable
class ClientProtocol(Protocol):
    """common interface for all API clients."""

    base_url: str

    async def get(self, path: str, **kwargs: Any) -> httpx.Response: ...
    async def post(self, path: str, **kwargs: Any) -> httpx.Response: ...
    async def close(self) -> None: ...
    async def __aenter__(self) -> ClientProtocol: ...
    async def __aexit__(self, *args: Any) -> None: ...
