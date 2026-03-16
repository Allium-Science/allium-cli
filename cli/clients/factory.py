from __future__ import annotations

import sys
from collections.abc import Callable
from typing import Any

from cli.clients.http import AlliumHTTPClient
from cli.clients.protocol import ClientProtocol
from cli.clients.x402 import X402Client
from cli.constants.config import EXIT_AUTH
from cli.types.profiles import (
    ApiKeyProfile,
    ProfileUnion,
    TempoProfile,
    X402KeyProfile,
    X402PrivyProfile,
)
from cli.utils.console import err_console


class _X402SignerAdapter:
    """adapts auth provider to X402Signer protocol."""

    def __init__(
        self,
        wallet_address: str,
        sign_fn: Callable[[dict[str, Any]], str],
        target_network: str,
    ) -> None:
        self._address = wallet_address
        self._sign_fn = sign_fn
        self._target_network = target_network

    @property
    def address(self) -> str:
        return self._address

    @property
    def target_network(self) -> str:
        return self._target_network

    def sign(self, typed_data: dict[str, Any]) -> str:
        return self._sign_fn(typed_data)


def _make_x402_client(
    base_url: str,
    make_signer: Callable[..., tuple[str, Callable[[dict[str, Any]], str]]],
    profile: X402KeyProfile | X402PrivyProfile,
) -> X402Client:
    try:
        address, sign_fn = make_signer(profile)
    except Exception as exc:
        err_console.print(f"[red]Failed to initialize wallet signer:[/red] {exc}")
        sys.exit(EXIT_AUTH)
    signer = _X402SignerAdapter(address, sign_fn, str(profile.target_network))
    http = AlliumHTTPClient(base_url=base_url)
    return X402Client(http, signer)


def get_client(profile: ProfileUnion) -> ClientProtocol:
    """create an authenticated client from a profile."""
    base_url = profile.base_url

    if isinstance(profile, ApiKeyProfile):
        from cli.auth.api_key import get_headers

        return AlliumHTTPClient(base_url=base_url, headers=get_headers(profile))

    if isinstance(profile, X402KeyProfile):
        from cli.auth.x402_key import make_signer

        return _make_x402_client(base_url, make_signer, profile)

    if isinstance(profile, X402PrivyProfile):
        from cli.auth.x402_privy import make_signer

        return _make_x402_client(base_url, make_signer, profile)

    if isinstance(profile, TempoProfile):
        from cli.clients.tempo import TempoClient

        try:
            return TempoClient(profile)
        except Exception as exc:
            err_console.print(f"[red]Failed to initialize Tempo client:[/red] {exc}")
            sys.exit(EXIT_AUTH)

    raise ValueError(f"Unknown profile type: {type(profile)}")
