from __future__ import annotations

import base64
import json

import pytest

from cli.clients.x402 import _build_payment_header


class DummySigner:
    address = "0x1111111111111111111111111111111111111111"
    target_network = "eip155:8453"

    def __init__(self) -> None:
        self.typed_data: dict | None = None

    def sign(self, typed_data: dict) -> str:
        self.typed_data = typed_data
        return "0xsigned"


@pytest.mark.parametrize("timeout_value", [300, "300"])
def test_build_payment_header_uses_absolute_valid_before(
    monkeypatch: pytest.MonkeyPatch,
    timeout_value: int | str,
) -> None:
    fixed_now = 1_700_000_000
    expected_valid_before = str(fixed_now + int(timeout_value))
    expected_nonce = "0x" + ("ab" * 32)

    monkeypatch.setattr("cli.clients.x402.time.time", lambda: fixed_now)
    monkeypatch.setattr("cli.clients.x402.secrets.token_hex", lambda n: "ab" * n)

    signer = DummySigner()
    response_body = {
        "x402Version": 2,
        "resource": {
            "url": "https://api.example.com/resource",
            "description": "test resource",
            "mimeType": "application/json",
        },
    }
    option = {
        "scheme": "exact",
        "network": "eip155:8453",
        "amount": "10000",
        "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        "payTo": "0x209693Bc6afc0C5328bA36FaF03C514EF312287C",
        "maxTimeoutSeconds": timeout_value,
        "extra": {"name": "USD Coin", "version": "2"},
    }

    encoded = _build_payment_header(
        response_body=response_body,
        option=option,
        signer=signer,
        url="https://api.example.com/resource",
    )

    payload = json.loads(base64.b64decode(encoded).decode())

    assert signer.typed_data is not None
    assert signer.typed_data["message"]["validBefore"] == expected_valid_before
    assert signer.typed_data["message"]["nonce"] == expected_nonce

    authorization = payload["payload"]["authorization"]
    assert authorization["validBefore"] == expected_valid_before
    assert authorization["nonce"] == expected_nonce
