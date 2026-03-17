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
        domain = typed_data["domain"]
        msg = typed_data["message"]
        primary = typed_data.get("primary_type", typed_data.get("primaryType"))
        types = {k: v for k, v in typed_data["types"].items() if k != "EIP712Domain"}
        signable = encode_typed_data(
            primaryType=primary,
            domain_data=domain,
            types=types,
            message=msg,
        )
        signed = account.sign_message(signable)
        return signed.signature.hex()

    return address, sign
