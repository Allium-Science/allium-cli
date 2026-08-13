from __future__ import annotations

import base64
import json
from typing import Any
from unittest.mock import patch

from cli.clients.x402 import _build_payment_header, _select_payment_option


class _FakeSigner:
    address = "0x" + "11" * 20
    target_network = "eip155:8453"

    def __init__(self) -> None:
        self.last_typed_data: dict[str, Any] | None = None

    def sign(self, typed_data: dict[str, Any]) -> str:
        self.last_typed_data = typed_data
        return "0xsig"


def _option(max_timeout_seconds: int = 60) -> dict[str, Any]:
    return {
        "scheme": "exact",
        "network": "eip155:8453",
        "amount": "1000",
        "asset": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        "payTo": "0x" + "22" * 20,
        "maxTimeoutSeconds": max_timeout_seconds,
        "extra": {"name": "USD Coin", "version": "2"},
    }


def _response_body(option: dict[str, Any]) -> dict[str, Any]:
    return {
        "x402Version": 1,
        "accepts": [option],
        "resource": {"url": "https://api.allium.so/x"},
    }


def test_select_payment_option_matches_network() -> None:
    option = _option()
    body = _response_body(option)
    assert _select_payment_option(body, "eip155:8453") is option


def test_build_payment_header_valid_before_is_unix_timestamp() -> None:
    option = _option(max_timeout_seconds=60)
    body = _response_body(option)
    signer = _FakeSigner()
    now = 1_700_000_000

    with patch("cli.clients.x402.time.time", return_value=now):
        header = _build_payment_header(body, option, signer, "https://api.allium.so/x")

    assert signer.last_typed_data is not None
    expected = str(now + 60)
    assert signer.last_typed_data["message"]["validBefore"] == expected

    payload = json.loads(base64.b64decode(header))
    assert payload["payload"]["authorization"]["validBefore"] == expected
    assert int(expected) == now + 60
    assert int(expected) > now
