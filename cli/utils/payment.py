from __future__ import annotations

import httpx

from cli.utils.cost_log import cost_log


def log_successful_payment(
    *,
    response: httpx.Response,
    method: str,
    endpoint: str,
    network: str,
    raw_amount: str | int,
    token: str,
    wallet: str,
) -> None:
    """log a machine payment if the response indicates success."""
    if response.status_code < 400:
        cost_log.log_payment(
            method=method,
            endpoint=endpoint,
            network=network,
            raw_amount=raw_amount,
            token=token,
            wallet=wallet,
            http_status=response.status_code,
        )
