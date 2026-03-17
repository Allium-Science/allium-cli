from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import httpx
from mpp import Challenge
from mpp.client.transport import PaymentTransport
from mpp.methods.tempo import ChargeIntent, TempoAccount, tempo
from mpp.methods.tempo._defaults import CHAIN_RPC_URLS

from cli.types.profiles import TempoProfile

logger = logging.getLogger(__name__)


@dataclass
class TempoPaymentInfo:
    """cost details from the most recent 402 challenge."""

    amount: str = "0"
    currency: str = ""
    recipient: str = ""


class _CostCapturingTransport(httpx.AsyncBaseTransport):
    """captures payment amounts from 402 challenges during transport."""

    def __init__(self, inner: httpx.AsyncBaseTransport | None = None) -> None:
        self._inner = inner or httpx.AsyncHTTPTransport()
        self.last_payment = TempoPaymentInfo()

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        response = await self._inner.handle_async_request(request)
        if response.status_code == 402:
            self._capture_challenge(response)
        return response

    def _capture_challenge(self, response: httpx.Response) -> None:
        for header in response.headers.get_list("www-authenticate"):
            if not header.lower().startswith("payment "):
                continue
            try:
                challenge = Challenge.from_www_authenticate(header)
                req = challenge.request
                self.last_payment = TempoPaymentInfo(
                    amount=str(req.get("amount", "0")),
                    currency=str(req.get("currency", "")),
                    recipient=str(req.get("recipient", "")),
                )
                return
            except Exception:
                logger.debug("Failed to parse challenge header", exc_info=True)

    async def aclose(self) -> None:
        await self._inner.aclose()


@dataclass
class TempoResult:
    """bundles HTTP response with payment metadata."""

    response: httpx.Response
    payment: TempoPaymentInfo


def _get_tempo_config(profile: TempoProfile) -> tuple[TempoAccount, str, int]:
    chain_id = int(profile.chain_id)
    rpc_url = CHAIN_RPC_URLS.get(chain_id)
    if rpc_url is None:
        supported = ", ".join(str(cid) for cid in sorted(CHAIN_RPC_URLS))
        raise ValueError(
            f"Unsupported Tempo chain ID: {chain_id}. Supported chain IDs: {supported}"
        )
    account = TempoAccount.from_key(profile.private_key)
    return account, rpc_url, chain_id


async def tempo_request(
    profile: TempoProfile,
    method: str,
    url: str,
    **kwargs: Any,
) -> TempoResult:
    account, rpc_url, _ = _get_tempo_config(profile)
    kwargs.setdefault("timeout", 30.0)

    cost_transport = _CostCapturingTransport()
    payment_transport = PaymentTransport(
        methods=[
            tempo(
                account=account,
                rpc_url=rpc_url,
                intents={"charge": ChargeIntent()},
            )
        ],
        inner=cost_transport,
    )

    async with httpx.AsyncClient(transport=payment_transport) as client:
        response = await client.request(method, url, **kwargs)
        return TempoResult(response=response, payment=cost_transport.last_payment)
