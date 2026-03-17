from __future__ import annotations

from collections.abc import Callable
from typing import Any

from privy import PrivyAPI

from cli.types.profiles import X402PrivyProfile


def make_signer(
    profile: X402PrivyProfile,
) -> tuple[str, Callable[[dict[str, Any]], str]]:
    """return (wallet_address, sign_fn) for x402 using privy wallet RPC."""
    privy = PrivyAPI(app_id=profile.privy_app_id, app_secret=profile.privy_app_secret)
    wallet = privy.wallets.get(wallet_id=profile.privy_wallet_id)
    address: str = wallet.address

    def sign(typed_data: dict[str, Any]) -> str:
        result = privy.wallets.rpc(
            wallet_id=profile.privy_wallet_id,
            method="eth_signTypedData_v4",
            params={"typed_data": typed_data},
        )
        return result.data.signature

    return address, sign
