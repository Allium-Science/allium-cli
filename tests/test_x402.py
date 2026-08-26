from __future__ import annotations

import base64
import json
import time
from typing import Any

import pytest

from cli.clients.x402 import (
    VALID_AFTER_SKEW_SECONDS,
    _build_payment_header,
    _select_payment_option,
)

MAX_TIMEOUT_SECONDS = 60


class FakeSigner:
    """Captures the typed data it is asked to sign."""

    def __init__(self) -> None:
        self.typed_data: dict[str, Any] | None = None

    @property
    def address(self) -> str:
        return "0x1111111111111111111111111111111111111111"

    @property
    def target_network(self) -> str:
        return "eip155:8453"

    def sign(self, typed_data: dict[str, Any]) -> str:
        self.typed_data = typed_data
        return "0xsignature"


@pytest.fixture()
def option():
    return {
        "scheme": "exact",
        "network": "eip155:8453",
        "amount": "1000",
        "asset": "0x2222222222222222222222222222222222222222",
        "payTo": "0x3333333333333333333333333333333333333333",
        "maxTimeoutSeconds": MAX_TIMEOUT_SECONDS,
        "extra": {"name": "USD Coin", "version": "2"},
    }


@pytest.fixture()
def response_body(option):
    return {"x402Version": 1, "accepts": [option]}


def _decode(header: str) -> dict[str, Any]:
    return json.loads(base64.b64decode(header).decode())


class TestSelectPaymentOption:
    def test_selects_matching_network(self, response_body, option):
        assert _select_payment_option(response_body, "eip155:8453") == option

    def test_raises_for_unavailable_network(self, response_body):
        with pytest.raises(ValueError, match="No payment option"):
            _select_payment_option(response_body, "eip155:1")


class TestAuthorizationValidityWindow:
    """EIP-3009 validAfter/validBefore are absolute unix timestamps.

    The token contract enforces `block.timestamp < validBefore`, so signing the
    raw `maxTimeoutSeconds` duration produced a deadline in 1970 and every
    authorization was expired before it was submitted.
    """

    def test_valid_before_is_in_the_future(self, response_body, option):
        before = int(time.time())
        header = _build_payment_header(
            response_body=response_body,
            option=option,
            signer=FakeSigner(),
            url="https://api.example.com/v1/thing",
        )
        auth = _decode(header)["payload"]["authorization"]

        assert int(auth["validBefore"]) >= before + MAX_TIMEOUT_SECONDS
        assert int(auth["validBefore"]) > int(time.time())

    def test_valid_after_is_already_past(self, response_body, option):
        header = _build_payment_header(
            response_body=response_body,
            option=option,
            signer=FakeSigner(),
            url="https://api.example.com/v1/thing",
        )
        auth = _decode(header)["payload"]["authorization"]

        now = int(time.time())
        assert int(auth["validAfter"]) <= now
        # Backdated for clock skew, but not unboundedly so.
        assert int(auth["validAfter"]) >= now - VALID_AFTER_SKEW_SECONDS - 5

    def test_window_spans_the_advertised_timeout(self, response_body, option):
        header = _build_payment_header(
            response_body=response_body,
            option=option,
            signer=FakeSigner(),
            url="https://api.example.com/v1/thing",
        )
        auth = _decode(header)["payload"]["authorization"]

        span = int(auth["validBefore"]) - int(auth["validAfter"])
        assert span >= MAX_TIMEOUT_SECONDS

    def test_signed_typed_data_matches_submitted_authorization(
        self, response_body, option
    ):
        """The signature must cover exactly the authorization that is sent."""
        signer = FakeSigner()
        header = _build_payment_header(
            response_body=response_body,
            option=option,
            signer=signer,
            url="https://api.example.com/v1/thing",
        )
        auth = _decode(header)["payload"]["authorization"]

        assert signer.typed_data is not None
        message = signer.typed_data["message"]
        for field in ("from", "to", "value", "validAfter", "validBefore", "nonce"):
            assert message[field] == auth[field], field
