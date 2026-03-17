from __future__ import annotations

from collections.abc import Callable
from typing import Any

from eth_account import Account
from eth_account.messages import encode_typed_data

from cli.types.profiles import X402KeyProfile


def make_signer(profile: X402KeyProfile) -> tuple[str, Callable[[dict[str, Any]], str]]:
    """return (wallet_address, sign_fn) for x402 using a raw private key."""
    account = Account.from_key(profile.private_key)
    address: str = account.address

    def sign(typed_data: dict[str, Any]) -> str:
        full_message = {
            "types": typed_data["types"],
            "primaryType": typed_data.get(
                "primary_type", typed_data.get("primaryType")
            ),
            "domain": typed_data["domain"],
            "message": typed_data["message"],
        }
        signable = encode_typed_data(full_message=full_message)
        signed = account.sign_message(signable)
        return f"0x{signed.signature.hex()}"

    return address, sign
