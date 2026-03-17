from __future__ import annotations

ALL_NETWORK_LABELS: dict[str, str] = {
    "eip155:8453": "Base Mainnet",
    "4217": "Tempo Mainnet",
}

METHOD_LABELS: dict[str, str] = {
    "api_key": "API Key",
    "x402_key": "x402 Private Key",
    "x402_privy": "x402 Privy",
    "x402": "x402",
    "tempo": "Tempo",
}


def network_label(network_id: str) -> str:
    """human-readable label for a network/chain ID."""
    return ALL_NETWORK_LABELS.get(network_id, network_id)


def method_label(method_id: str) -> str:
    """human-readable label for an auth method."""
    return METHOD_LABELS.get(method_id, method_id)
