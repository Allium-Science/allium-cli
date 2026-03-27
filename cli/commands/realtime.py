from __future__ import annotations

from typing import Any

import rich_click as click

from cli.utils.async_cmd import async_command
from cli.utils.body import (
    load_body_or_build,
    pair_chain_items,
    pair_chain_items_with_token,
)
from cli.utils.errors import output_response, resolve_client
from cli.utils.options import (
    chain_address_options,
    chain_address_token_options,
    chain_token_options,
)
from cli.utils.time import (
    RANGE_END_TIMESTAMP_HELP,
    RANGE_START_TIMESTAMP_HELP,
    default_range_end_timestamp_utc,
    default_range_start_timestamp_utc,
)


@click.group()
@click.pass_context
def realtime(ctx: click.Context) -> None:
    """query realtime blockchain data with 3-5s freshness across 20+ chains.

    \b
    available subcommands:
      prices         token prices from on-chain DEX trades
      tokens         token metadata, search, and lookup
      balances       wallet token balances (current and historical)
      holdings       wallet token holdings (historical)
      transactions   wallet transaction activity with labels
      pnl            wallet profit and loss calculations (current and historical)
      pnl-by-token   wallet token PnL by token address (current and historical)
      supported-chains  list chains supported by the realtime APIs
    """


# supported chains


@realtime.command("supported-chains")
@click.pass_context
@async_command
async def supported_chains(ctx: click.Context) -> None:
    """list chains supported by the realtime APIs."""
    client = resolve_client(ctx)
    resp = await client.get("/api/v1/supported-chains/realtime-apis/simple")
    output_response(ctx, resp)


# prices


@realtime.group()
@click.pass_context
def prices(ctx: click.Context) -> None:
    """token prices derived from on-chain DEX trades.

    prices use VWAP calculation with outlier detection and update every minute
    from tracked DEXes across supported chains.
    """


@prices.command("latest")
@chain_token_options
@click.pass_context
@async_command
async def prices_latest(
    ctx: click.Context,
    chain: tuple[str, ...],
    token_address: tuple[str, ...],
    body: str | None,
) -> None:
    """fetch the latest minute-level price and OHLC values for tokens.

    returns the most recent completed minute interval. falls back to last
    known price for inactive tokens (up to 7 days).
    """
    client = resolve_client(ctx)

    def build() -> list[dict[str, str]]:
        return pair_chain_items(chain, token_address, address_key="token_address")

    payload = load_body_or_build(body, build)
    resp = await client.post("/api/v1/developer/prices", json=payload)
    output_response(ctx, resp)


@prices.command("at-timestamp")
@chain_token_options
@click.option(
    "--timestamp",
    required=False,
    help="ISO 8601 timestamp, e.g. 2026-01-15T12:00:00Z.",
)
@click.option(
    "--time-granularity",
    required=False,
    type=click.Choice(["15s", "1m", "5m", "1h", "1d"]),
    help="Aggregation interval for price data.",
)
@click.pass_context
@async_command
async def prices_at_timestamp(
    ctx: click.Context,
    chain: tuple[str, ...],
    token_address: tuple[str, ...],
    timestamp: str | None,
    time_granularity: str | None,
    body: str | None,
) -> None:
    """fetch token prices at a specific point in time.

    supports granularities from 15-second to daily intervals.
    """
    client = resolve_client(ctx)

    def build() -> dict[str, Any]:
        addresses = pair_chain_items(chain, token_address, address_key="token_address")
        payload: dict[str, Any] = {"addresses": addresses}
        if timestamp:
            payload["timestamp"] = timestamp
        if time_granularity:
            payload["time_granularity"] = time_granularity
        return payload

    payload = load_body_or_build(body, build)
    resp = await client.post("/api/v1/developer/prices/at-timestamp", json=payload)
    output_response(ctx, resp)


@prices.command("history")
@chain_token_options
@click.option(
    "--start-timestamp",
    default=default_range_start_timestamp_utc,
    help=RANGE_START_TIMESTAMP_HELP,
)
@click.option(
    "--end-timestamp",
    default=default_range_end_timestamp_utc,
    help=RANGE_END_TIMESTAMP_HELP,
)
@click.option(
    "--time-granularity",
    default="1d",
    type=click.Choice(["15s", "1m", "5m", "1h", "1d"]),
    help="Aggregation interval for price data.",
)
@click.option(
    "--cursor",
    default=None,
    help="Cursor for pagination.",
)
@click.pass_context
@async_command
async def prices_history(
    ctx: click.Context,
    chain: tuple[str, ...],
    token_address: tuple[str, ...],
    start_timestamp: str,
    end_timestamp: str,
    time_granularity: str,
    cursor: str | None,
    body: str | None,
) -> None:
    """fetch historical price series for tokens over a time range.

    useful for charting, backtesting, and trend analysis.
    """
    client = resolve_client(ctx)

    def build() -> dict[str, Any]:
        addresses = pair_chain_items(chain, token_address, address_key="token_address")
        payload: dict[str, Any] = {
            "addresses": addresses,
            "start_timestamp": start_timestamp,
            "end_timestamp": end_timestamp,
            "time_granularity": time_granularity,
        }
        return payload

    payload = load_body_or_build(body, build)
    params: dict[str, Any] = {}
    if cursor is not None:
        params["cursor"] = cursor
    resp = await client.post(
        "/api/v1/developer/prices/history", json=payload, params=params
    )
    output_response(ctx, resp)


@prices.command("stats")
@chain_token_options
@click.pass_context
@async_command
async def prices_stats(
    ctx: click.Context,
    chain: tuple[str, ...],
    token_address: tuple[str, ...],
    body: str | None,
) -> None:
    """fetch 24h and 1h price statistics.

    returns high, low, volume, trade count, and percent change.
    """
    client = resolve_client(ctx)

    def build() -> list[dict[str, str]]:
        return pair_chain_items(chain, token_address, address_key="token_address")

    payload = load_body_or_build(body, build)
    resp = await client.post("/api/v1/developer/prices/stats", json=payload)
    output_response(ctx, resp)


# tokens


@realtime.group()
@click.pass_context
def tokens(ctx: click.Context) -> None:
    """token metadata and search across supported chains."""


@tokens.command("list")
@click.option(
    "--chain", default=None, help="Filter by blockchain name, e.g. ethereum, solana."
)
@click.option(
    "--sort",
    default="volume",
    type=click.Choice(
        ["volume", "trade_count", "fully_diluted_valuation", "address", "name"]
    ),
    help="Field to sort results by.",
)
@click.option(
    "--order",
    default="desc",
    type=click.Choice(["asc", "desc"]),
    help="Sort direction.",
)
@click.option(
    "--limit",
    default=200,
    type=click.IntRange(0, 200),
    help="Max results (up to 200).",
)
@click.pass_context
@async_command
async def tokens_list(
    ctx: click.Context,
    chain: str | None,
    sort: str,
    order: str,
    limit: int,
) -> None:
    """list top tokens sorted by volume, trade count, or FDV."""
    client = resolve_client(ctx)
    params: dict[str, Any] = {"sort": sort, "order": order, "limit": limit}
    if chain:
        params["chain"] = chain
    resp = await client.get("/api/v1/developer/tokens", params=params)
    output_response(ctx, resp)


@tokens.command("search")
@click.option(
    "--query", "-q", required=True, help="Search string (name or ticker symbol)."
)
@click.option(
    "--chain", default=None, help="Filter by blockchain name, e.g. ethereum, solana."
)
@click.option(
    "--limit",
    default=200,
    type=click.IntRange(0, 200),
    help="Max results (up to 200).",
)
@click.pass_context
@async_command
async def tokens_search(
    ctx: click.Context,
    query: str,
    chain: str | None,
    limit: int,
) -> None:
    """fuzzy search tokens by name or ticker symbol."""
    client = resolve_client(ctx)
    params: dict[str, Any] = {"q": query, "limit": limit}
    if chain:
        params["chain"] = chain
    resp = await client.get("/api/v1/developer/tokens/search", params=params)
    output_response(ctx, resp)


@tokens.command("chain-address")
@chain_token_options
@click.pass_context
@async_command
async def tokens_chain_address(
    ctx: click.Context,
    chain: tuple[str, ...],
    token_address: tuple[str, ...],
    body: str | None,
) -> None:
    """look up tokens by exact chain and contract address pairs."""
    client = resolve_client(ctx)

    def build() -> list[dict[str, str]]:
        return pair_chain_items(chain, token_address, address_key="token_address")

    payload = load_body_or_build(body, build)
    resp = await client.post("/api/v1/developer/tokens/chain-address", json=payload)
    output_response(ctx, resp)


# balances


@realtime.group()
@click.pass_context
def balances(ctx: click.Context) -> None:
    """wallet token balances, current or historical."""


@balances.command("latest")
@chain_address_options
@click.pass_context
@async_command
async def balances_latest(
    ctx: click.Context,
    chain: tuple[str, ...],
    address: tuple[str, ...],
    body: str | None,
) -> None:
    """fetch current token balances for one or more wallets."""
    client = resolve_client(ctx)

    def build() -> list[dict[str, str]]:
        return pair_chain_items(chain, address)

    payload = load_body_or_build(body, build)
    resp = await client.post("/api/v1/developer/wallet/balances", json=payload)
    output_response(ctx, resp)


@balances.command("history")
@chain_address_options
@click.option(
    "--start-timestamp",
    default=default_range_start_timestamp_utc,
    help=RANGE_START_TIMESTAMP_HELP,
)
@click.option(
    "--end-timestamp",
    default=default_range_end_timestamp_utc,
    help=RANGE_END_TIMESTAMP_HELP,
)
@click.option(
    "--limit",
    default=None,
    type=click.IntRange(1, 5000),
    help="Max results (up to 5000).",
)
@click.option(
    "--cursor",
    default=None,
    help="Cursor for pagination.",
)
@click.pass_context
@async_command
async def balances_history(
    ctx: click.Context,
    chain: tuple[str, ...],
    address: tuple[str, ...],
    start_timestamp: str,
    end_timestamp: str,
    limit: int | None,
    cursor: str | None,
    body: str | None,
) -> None:
    """fetch historical token balance snapshots (raw) over a time range."""
    client = resolve_client(ctx)

    def build() -> dict[str, Any]:
        addresses = pair_chain_items(chain, address)
        payload: dict[str, Any] = {"addresses": addresses}
        payload["start_timestamp"] = start_timestamp
        payload["end_timestamp"] = end_timestamp
        return payload

    payload = load_body_or_build(body, build)
    params: dict[str, Any] = {}
    if limit is not None:
        params["limit"] = limit
    if cursor is not None:
        params["cursor"] = cursor
    resp = await client.post(
        "/api/v1/developer/wallet/balances/history", json=payload, params=params
    )
    output_response(ctx, resp)


# transactions


@realtime.command("transactions")
@chain_address_options
@click.option(
    "--activity-type",
    default=None,
    help="Filter by activity type, e.g. dex_trade, transfer.",
)
@click.option(
    "--lookback-days", default=None, type=int, help="Lookback window in days."
)
@click.option(
    "--limit",
    default=None,
    type=click.IntRange(1, 1000),
    help="Max results (up to 1000).",
)
@click.option(
    "--cursor",
    default=None,
    help="Cursor for pagination.",
)
@click.pass_context
@async_command
async def transactions(
    ctx: click.Context,
    chain: tuple[str, ...],
    address: tuple[str, ...],
    activity_type: str | None,
    lookback_days: int | None,
    limit: int | None,
    cursor: str | None,
    body: str | None,
) -> None:
    """fetch transaction activity for wallets.

    includes decoded activities, asset transfers, and address labels.
    """
    client = resolve_client(ctx)

    def build() -> list[dict[str, str]]:
        return pair_chain_items(chain, address)

    payload = load_body_or_build(body, build)
    params: dict[str, Any] = {}
    if activity_type:
        params["activity_type"] = activity_type
    if lookback_days is not None:
        params["lookback_days"] = lookback_days
    if limit is not None:
        params["limit"] = limit
    if cursor is not None:
        params["cursor"] = cursor
    resp = await client.post(
        "/api/v1/developer/wallet/transactions", json=payload, params=params
    )
    output_response(ctx, resp)


# holdings


@realtime.group()
@click.pass_context
def holdings(ctx: click.Context) -> None:
    """wallet token holdings"""


@holdings.command("history")
@chain_address_options
@click.option(
    "--start-timestamp",
    default=default_range_start_timestamp_utc,
    help=RANGE_START_TIMESTAMP_HELP,
)
@click.option(
    "--end-timestamp",
    default=default_range_end_timestamp_utc,
    help=RANGE_END_TIMESTAMP_HELP,
)
@click.option(
    "--granularity",
    required=False,
    default="1d",
    type=click.Choice(["15s", "1m", "5m", "1h", "1d"]),
    help="Aggregation interval for holdings data.",
)
@click.option(
    "--min-liquidity",
    default=0.0,
    type=float,
    help="Minimum liquidity for token pairs.",
)
@click.pass_context
@async_command
async def holdings_history(
    ctx: click.Context,
    chain: tuple[str, ...],
    address: tuple[str, ...],
    start_timestamp: str,
    end_timestamp: str,
    granularity: str,
    min_liquidity: float,
    body: str | None,
) -> None:
    """calculate historical token holdings (USD value) over a time range."""
    client = resolve_client(ctx)

    def build() -> dict[str, Any]:
        addresses = pair_chain_items(chain, address)
        payload: dict[str, Any] = {"addresses": addresses}
        payload["start_timestamp"] = start_timestamp
        payload["end_timestamp"] = end_timestamp
        payload["granularity"] = granularity
        return payload

    payload = load_body_or_build(body, build)
    params: dict[str, Any] = {}
    if min_liquidity:
        params["min_liquidity"] = min_liquidity
    resp = await client.post(
        "/api/v1/developer/wallet/holdings/history", json=payload, params=params
    )
    output_response(ctx, resp)


# pnl


@realtime.group()
@click.pass_context
def pnl(ctx: click.Context) -> None:
    """wallet token PnL, current or historical."""


@pnl.command("latest")
@chain_address_options
@click.option(
    "--min-liquidity",
    default=0.0,
    type=float,
    help="Minimum liquidity for token pairs.",
)
@click.pass_context
@async_command
async def pnl_latest(
    ctx: click.Context,
    chain: tuple[str, ...],
    address: tuple[str, ...],
    min_liquidity: float,
    body: str | None,
) -> None:
    """calculate current realized and unrealized profit and loss for wallets.

    optionally include a historical breakdown over time with
    --with-historical-breakdown.
    """
    client = resolve_client(ctx)

    def build() -> list[dict[str, str]]:
        return pair_chain_items(chain, address)

    payload = load_body_or_build(body, build)
    params: dict[str, Any] = {}
    if min_liquidity:
        params["min_liquidity"] = min_liquidity
    resp = await client.post(
        "/api/v1/developer/wallet/pnl", json=payload, params=params
    )
    output_response(ctx, resp)


@pnl.command("history")
@chain_address_options
@click.option(
    "--start-timestamp",
    default=default_range_start_timestamp_utc,
    help=RANGE_START_TIMESTAMP_HELP,
)
@click.option(
    "--end-timestamp",
    default=default_range_end_timestamp_utc,
    help=RANGE_END_TIMESTAMP_HELP,
)
@click.option(
    "--granularity",
    required=False,
    default="1d",
    type=click.Choice(["15s", "1m", "5m", "1h", "1d"]),
    help="Aggregation interval for PnL data.",
)
@click.option(
    "--min-liquidity",
    default=0.0,
    type=float,
    help="Minimum liquidity for token pairs.",
)
@click.pass_context
@async_command
async def pnl_history(
    ctx: click.Context,
    chain: tuple[str, ...],
    address: tuple[str, ...],
    start_timestamp: str,
    end_timestamp: str,
    min_liquidity: float,
    granularity: str,
    body: str | None,
) -> None:
    """calculate historical realized and unrealized PnL over a time range."""
    client = resolve_client(ctx)

    def build() -> dict[str, Any]:
        addresses = pair_chain_items(chain, address)
        payload: dict[str, Any] = {"addresses": addresses}
        payload["start_timestamp"] = start_timestamp
        payload["end_timestamp"] = end_timestamp
        payload["granularity"] = granularity
        return payload

    payload = load_body_or_build(body, build)
    params: dict[str, Any] = {}
    if min_liquidity:
        params["min_liquidity"] = min_liquidity
    resp = await client.post(
        "/api/v1/developer/wallet/pnl/history", json=payload, params=params
    )
    output_response(ctx, resp)


@realtime.group()
@click.pass_context
def pnl_by_token(ctx: click.Context) -> None:
    """wallet token PnL by token address, current or historical."""


@pnl_by_token.command("latest")
@chain_address_token_options
@click.pass_context
@async_command
async def pnl_by_token_latest(
    ctx: click.Context,
    chain: tuple[str, ...],
    address: tuple[str, ...],
    token_address: tuple[str, ...],
    body: str | None,
) -> None:
    """calculate current realized and unrealized profit and loss
    for a specific token."""
    client = resolve_client(ctx)

    def build() -> list[dict[str, str]]:
        return pair_chain_items_with_token(chain, address, token_address)

    payload = load_body_or_build(body, build)
    params: dict[str, Any] = {}

    resp = await client.post(
        "/api/v1/developer/wallet/pnl-by-token", json=payload, params=params
    )
    output_response(ctx, resp)


@pnl_by_token.command("history")
@chain_address_token_options
@click.option(
    "--start-timestamp",
    default=default_range_start_timestamp_utc,
    help=RANGE_START_TIMESTAMP_HELP,
)
@click.option(
    "--end-timestamp",
    default=default_range_end_timestamp_utc,
    help=RANGE_END_TIMESTAMP_HELP,
)
@click.option(
    "--granularity",
    required=False,
    default="1d",
    type=click.Choice(["15s", "1m", "5m", "1h", "1d"]),
    help="Aggregation interval for PnL data.",
)
@click.pass_context
@async_command
async def pnl_by_token_history(
    ctx: click.Context,
    chain: tuple[str, ...],
    address: tuple[str, ...],
    token_address: tuple[str, ...],
    start_timestamp: str,
    end_timestamp: str,
    granularity: str,
    body: str | None,
) -> None:
    """calculate historical realized and unrealized PnL for a specific token."""
    client = resolve_client(ctx)

    def build() -> dict[str, Any]:
        addresses = pair_chain_items_with_token(chain, address, token_address)
        payload: dict[str, Any] = {
            "addresses": addresses,
            "start_timestamp": start_timestamp,
            "end_timestamp": end_timestamp,
            "granularity": granularity,
        }
        return payload

    payload = load_body_or_build(body, build)
    resp = await client.post(
        "/api/v1/developer/wallet/pnl-by-token/history", json=payload
    )
    output_response(ctx, resp)
