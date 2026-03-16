from __future__ import annotations

import asyncio
import sys
from typing import Any

import httpx

from cli.constants.config import EXIT_ERROR
from cli.utils.console import err_console as console

DEFAULT_TIMEOUT = 30.0
MAX_429_RETRIES = 3
BACKOFF_FACTORS = [1.0, 2.0, 4.0]


class AlliumHTTPClient:
    """async HTTP client with retries and base URL resolution."""

    def __init__(
        self,
        base_url: str,
        headers: dict[str, str] | None = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers or {},
            timeout=timeout,
        )

    async def request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> httpx.Response:
        return await self._request_with_retry(method, path, **kwargs)

    async def get(self, path: str, **kwargs: Any) -> httpx.Response:
        return await self.request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs: Any) -> httpx.Response:
        return await self.request("POST", path, **kwargs)

    async def _request_with_retry(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> httpx.Response:
        last_response: httpx.Response | None = None

        for attempt in range(MAX_429_RETRIES + 1):
            try:
                response = await self._client.request(method, path, **kwargs)
            except httpx.TimeoutException:
                console.print("[red]Request timed out.[/red]")
                sys.exit(EXIT_ERROR)
            except httpx.TransportError as exc:
                console.print(
                    f"[red]Network error ({type(exc).__name__}).[/red] "
                    "Check your connection and try again."
                )
                sys.exit(EXIT_ERROR)

            if response.status_code == 429 and attempt < MAX_429_RETRIES:
                wait = BACKOFF_FACTORS[attempt]
                console.print(
                    f"[yellow]Rate limited (429). Retrying in {wait:.0f}s...[/yellow]"
                )
                await asyncio.sleep(wait)
                last_response = response
                continue

            if response.status_code == 500 and attempt == 0:
                console.print("[yellow]Server error (500). Retrying in 2s...[/yellow]")
                await asyncio.sleep(2.0)
                last_response = response
                continue

            return response

        return last_response or response  # type: ignore[possibly-undefined]

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> AlliumHTTPClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
