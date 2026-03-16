from __future__ import annotations

from typing import Any

import httpx

from cli.auth.tempo import tempo_request
from cli.types.profiles import TempoProfile


class TempoClient:
    """tempo MPP client matching the standard client interface."""

    def __init__(self, profile: TempoProfile) -> None:
        self._profile = profile
        self.base_url = profile.base_url.rstrip("/")

    @property
    def profile(self) -> TempoProfile:
        return self._profile

    async def request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        url = f"{self.base_url}{path}"
        result = await tempo_request(self._profile, method, url, **kwargs)

        if result.payment.amount != "0":
            from cli.utils.payment import log_successful_payment

            log_successful_payment(
                response=result.response,
                method="tempo",
                endpoint=path,
                network=str(self._profile.chain_id),
                raw_amount=result.payment.amount,
                token=result.payment.currency or "tempo",
                wallet="tempo-account",
            )

        return result.response

    async def get(self, path: str, **kwargs: Any) -> httpx.Response:
        return await self.request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs: Any) -> httpx.Response:
        return await self.request("POST", path, **kwargs)

    async def close(self) -> None:
        pass

    async def __aenter__(self) -> TempoClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        pass
