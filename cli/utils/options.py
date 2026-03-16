from __future__ import annotations

from collections.abc import Callable
from typing import Any

import rich_click as click

_CHAIN_OPT = click.option(
    "--chain",
    multiple=True,
    required=False,
    help="Blockchain name, e.g. ethereum, solana, base (repeatable).",
)
_TOKEN_ADDRESS_OPT = click.option(
    "--token-address",
    multiple=True,
    required=False,
    help="Token contract address (repeatable; pair with --chain).",
)
_WALLET_ADDRESS_OPT = click.option(
    "--address",
    multiple=True,
    required=False,
    help="Wallet address (repeatable; pair with --chain).",
)
_BODY_OPT = click.option(
    "--body",
    default=None,
    help="JSON payload or path to .json file. Overrides other options.",
)


def chain_token_options(f: Callable[..., Any]) -> Callable[..., Any]:
    """bundle --chain, --token-address, --body options."""
    for decorator in reversed([_CHAIN_OPT, _TOKEN_ADDRESS_OPT, _BODY_OPT]):
        f = decorator(f)
    return f


def chain_address_options(f: Callable[..., Any]) -> Callable[..., Any]:
    """bundle --chain, --address, --body options."""
    for decorator in reversed([_CHAIN_OPT, _WALLET_ADDRESS_OPT, _BODY_OPT]):
        f = decorator(f)
    return f
