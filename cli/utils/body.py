from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import rich_click as click


def load_body_or_build(
    body: str | None,
    build_fn: Any,
) -> Any:
    """load JSON from --body (file or inline), or call build_fn."""
    if body:
        path = Path(body)
        try:
            raw = path.read_text() if path.exists() else body
            return json.loads(raw)
        except json.JSONDecodeError as e:
            source = f"file '{path}'" if path.exists() else "inline value"
            raise click.UsageError(f"Invalid JSON in --body ({source}): {e}") from None
    return build_fn()


def pair_chain_items(
    chains: tuple[str, ...],
    addresses: tuple[str, ...],
    chain_key: str = "chain",
    address_key: str = "address",
) -> list[dict[str, str]]:
    """zip repeated --chain and --address flags into a list of dicts."""
    if not chains:
        raise click.UsageError("Provide at least one --chain (or use --body).")
    if len(chains) != len(addresses):
        n_chains, n_addrs = len(chains), len(addresses)
        raise click.UsageError(
            f"Mismatched --chain ({n_chains}) and address ({n_addrs}) counts."
        )
    return [{chain_key: c, address_key: a} for c, a in zip(chains, addresses)]


def pair_chain_items_with_token(
    chains: tuple[str, ...],
    addresses: tuple[str, ...],
    token_addresses: tuple[str, ...],
    chain_key: str = "chain",
    address_key: str = "address",
    token_address_key: str = "token_address",
) -> list[dict[str, str]]:
    """zip repeated --chain, --address, and --token-address flags
    into a list of dicts."""
    if not chains:
        raise click.UsageError("Provide at least one --chain (or use --body).")
    if len(chains) != len(addresses) or len(chains) != len(token_addresses):
        n_chains, n_addrs, n_tokens = len(chains), len(addresses), len(token_addresses)
        raise click.UsageError(
            f"Mismatched --chain ({n_chains}), address ({n_addrs}), "
            f"and token address ({n_tokens}) counts."
        )
    return [
        {chain_key: c, address_key: a, token_address_key: t}
        for c, a, t in zip(chains, addresses, token_addresses)
    ]
