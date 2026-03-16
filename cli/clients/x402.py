"""x402 payment flow: send request, handle 402 challenge, replay with signature."""

from __future__ import annotations

import base64
import json
import secrets
import sys
from typing import Any, Protocol

import httpx

from cli.clients.http import AlliumHTTPClient
from cli.constants.config import EXIT_ERROR
from cli.utils.console import err_console


class X402Signer(Protocol):
    """protocol for x402 payment signers."""

    @property
    def address(self) -> str: ...

    @property
    def target_network(self) -> str: ...

    def sign(self, typed_data: dict[str, Any]) -> str: ...


class X402Client:
    """wraps AlliumHTTPClient with automatic x402 payment handling."""

    def __init__(self, http_client: AlliumHTTPClient, signer: X402Signer) -> None:
        self._http = http_client
        self._signer = signer

    @property
    def base_url(self) -> str:
        return self._http.base_url

    async def request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        headers = kwargs.pop("headers", {})
        headers["X-Prefer-Payment"] = "x402"

        response = await self._http.request(method, path, headers=headers, **kwargs)
        if response.status_code != 402:
            return response

        try:
            response_body = response.json()
            option = _select_payment_option(response_body, self._signer.target_network)
            payment_header = _build_payment_header(
                response_body=response_body,
                option=option,
                signer=self._signer,
                url=f"{self._http.base_url}{path}",
            )
        except (KeyError, IndexError, ValueError, json.JSONDecodeError) as exc:
            err_console.print(f"[red]Malformed 402 payment challenge:[/red] {exc}")
            sys.exit(EXIT_ERROR)

        headers["PAYMENT-SIGNATURE"] = payment_header
        final_response = await self._http.request(
            method, path, headers=headers, **kwargs
        )

        from cli.utils.payment import log_successful_payment

        log_successful_payment(
            response=final_response,
            method="x402",
            endpoint=path,
            network=option["network"],
            raw_amount=option["amount"],
            token=option["asset"],
            wallet=self._signer.address,
        )

        return final_response

    async def get(self, path: str, **kwargs: Any) -> httpx.Response:
        return await self.request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs: Any) -> httpx.Response:
        return await self.request("POST", path, **kwargs)

    async def close(self) -> None:
        await self._http.close()

    async def __aenter__(self) -> X402Client:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()


def _select_payment_option(
    response_body: dict[str, Any], target_network: str
) -> dict[str, Any]:
    accepts = response_body.get("accepts", [])
    option = next((a for a in accepts if a["network"] == target_network), None)
    if option is None:
        available = [a["network"] for a in accepts]
        raise ValueError(
            f"No payment option for network '{target_network}'. Available: {available}"
        )
    return option


def _build_payment_header(
    response_body: dict[str, Any],
    option: dict[str, Any],
    signer: X402Signer,
    url: str,
) -> str:
    chain_id = int(option["network"].split(":")[1])
    nonce = "0x" + secrets.token_hex(32)

    typed_data = {
        "types": {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"},
            ],
            "TransferWithAuthorization": [
                {"name": "from", "type": "address"},
                {"name": "to", "type": "address"},
                {"name": "value", "type": "uint256"},
                {"name": "validAfter", "type": "uint256"},
                {"name": "validBefore", "type": "uint256"},
                {"name": "nonce", "type": "bytes32"},
            ],
        },
        "domain": {
            "name": option["extra"]["name"],
            "version": option["extra"]["version"],
            "chainId": chain_id,
            "verifyingContract": option["asset"],
        },
        "primary_type": "TransferWithAuthorization",
        "message": {
            "from": signer.address,
            "to": option["payTo"],
            "value": str(option["amount"]),
            "validAfter": "0",
            "validBefore": str(option["maxTimeoutSeconds"]),
            "nonce": nonce,
        },
    }

    signature = signer.sign(typed_data)

    resource = response_body.get("resource", {})
    payload = {
        "x402Version": response_body["x402Version"],
        "resource": {
            "url": resource.get("url", url),
            "description": resource.get("description", ""),
            "mimeType": resource.get("mimeType", "application/json"),
        },
        "accepted": {
            "scheme": option["scheme"],
            "network": option["network"],
            "amount": str(option["amount"]),
            "asset": option["asset"],
            "payTo": option["payTo"],
            "maxTimeoutSeconds": option["maxTimeoutSeconds"],
            "extra": option.get("extra", {}),
        },
        "payload": {
            "signature": signature,
            "authorization": {
                "from": signer.address,
                "to": option["payTo"],
                "value": str(option["amount"]),
                "validAfter": "0",
                "validBefore": str(option["maxTimeoutSeconds"]),
                "nonce": nonce,
            },
        },
    }

    return base64.b64encode(json.dumps(payload).encode()).decode()
