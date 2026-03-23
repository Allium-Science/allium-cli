# Allium CLI

Command-line interface for querying blockchain data across 80+ chains via the [Allium](https://allium.so) platform. Supports realtime token prices, wallet balances, transaction history, and SQL queries against Allium's data warehouse.

## Installation

```bash
curl -sSL https://raw.githubusercontent.com/Allium-Science/allium-cli/main/install.sh | sh
```

Or install directly with your preferred package manager:

```bash
uv tool install allium-cli   # recommended
pipx install allium-cli
pip install allium-cli
```

This installs the `allium` command. Run `allium auth setup` to configure authentication.

## Authentication

The CLI supports four authentication methods. Run the interactive wizard, or pass arguments directly for scripted/CI setups:

```bash
# Interactive wizard (arrow-key selection)
allium auth setup

# Non-interactive one-liners
allium auth setup --method api_key --api-key sk-...
allium auth setup --method x402_key --private-key 0x... --network eip155:8453
allium auth setup --method x402_privy \
    --privy-app-id ... --privy-app-secret ... \
    --privy-wallet-id ... --network eip155:8453
allium auth setup --method tempo --private-key 0x... --chain-id 4217
```

| Method | Description |
|---|---|
| **API Key** | Standard key from [app.allium.so/settings/api-keys](https://app.allium.so/settings/api-keys) |
| **x402 Private Key** | Pay-per-call with USDC on Base -- no API key needed |
| **x402 Privy** | x402 via Privy server wallets -- no private key handling |
| **Tempo MPP** | Tempo micropayment protocol |

Optional flags: `--name <profile-name>` (defaults to the method name), `--no-active` (skip setting as active profile).

Credentials are stored in `~/.config/allium/credentials.toml` (file permissions restricted to owner).

### Profile management

```bash
allium auth list          # Show all profiles
allium auth use <name>    # Switch active profile
allium auth remove <name> # Delete a profile
```

## Global Options

```
--profile TEXT             Override the active auth profile for this command
--format [json|table|csv]  Output format (default: json)
-v, --verbose              Show progress details (run IDs, spinners, status)
--help                     Show help and exit
```

## Commands

### `allium realtime` -- Realtime Blockchain Data

Query realtime blockchain data with 3-5s freshness across 20+ chains.

#### Prices

Token prices derived from on-chain DEX trades with VWAP calculation and outlier detection.

```bash
# Latest minute-level price and OHLC values
allium realtime prices latest \
  --chain solana --token-address So11111111111111111111111111111111111111112

# Price at a specific timestamp
allium realtime prices at-timestamp \
  --chain ethereum --token-address 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48 \
  --timestamp 2026-01-15T12:00:00Z --time-granularity 1h

# Historical price series
allium realtime prices history \
  --chain ethereum --token-address 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48 \
  --start-timestamp 2026-01-01T00:00:00Z --end-timestamp 2026-01-07T00:00:00Z \
  --time-granularity 1d

# Historical price series with cursor
allium realtime prices history \
  --chain solana --token-address So11111111111111111111111111111111111111112 \
  --start-timestamp 2024-08-17T13:00:00Z --end-timestamp 2025-08-17T20:00:00Z \
  --time-granularity 5m --cursor eyJzb2xhbmEiOiAiZXlKc1lYTjBYM1JwYldWemRHRnRjQ0k2SUNJeU1ESTBMVEV5TFRJeUlEQTJPalF3T2pBd0luMD0ifQ==

# 24h/1h price stats (high, low, volume, trade count, percent change)
allium realtime prices stats \
  --chain solana --token-address So11111111111111111111111111111111111111112
```

**Options:** `--chain`, `--token-address` (repeatable, paired in order), `--body` (JSON override), `--timestamp`, `--start-timestamp`, `--end-timestamp`, `--time-granularity [15s|1m|5m|1h|1d]`

#### Tokens

```bash
# List top tokens by volume
allium realtime tokens list --chain ethereum --sort volume --limit 10

# Fuzzy search by name or symbol
allium realtime tokens search -q "USDC"

# Exact lookup by chain + contract address
allium realtime tokens chain-address \
  --chain ethereum --token-address 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48
```

**Options:** `--chain`, `--token-address` (repeatable), `--sort [volume|trade_count|fully_diluted_valuation|address|name]`, `--order [asc|desc]`, `--limit`, `-q/--query`

#### Balances

```bash
# Current token balances for a wallet
allium realtime balances latest \
  --chain ethereum --address 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045

# Historical balance snapshots
allium realtime balances history \
  --chain ethereum --address 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045 \
  --start-timestamp 2026-01-01T00:00:00Z --limit 100
```

**Options:** `--chain`, `--address` (repeatable, paired), `--start-timestamp`, `--end-timestamp`, `--limit`, `--body`

#### Holdings

```bash
# Historical Wallet holdings
allium realtime holdings history \
  --chain ethereum \
  --address 0x3c96937a5bce135c47133702d54b652498e5e375 \
  --start-timestamp 2024-03-01T00:00:00Z \
  --end-timestamp 2026-03-21T00:00:00Z \
  --granularity 1d
```

**Options:** `--chain`, `--address` (repeatable), `--granularity`,  `--body`

#### Transactions

```bash
# Wallet transaction activity with decoded activities and labels
allium realtime transactions \
  --chain ethereum --address 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045 \
  --activity-type dex_trade --lookback-days 7 --limit 50
```

**Options:** `--chain`, `--address` (repeatable), `--activity-type`, `--lookback-days`, `--limit`, `--body`

#### PnL

##### Latest PnL

```bash
# Latest Wallet profit and loss
allium realtime pnl latest \
  --chain ethereum \
  --address 0x3c96937a5bce135c47133702d54b652498e5e375 \
  --min-liquidity 1000

# Latest Wallet profit and loss with historical breakdown
allium realtime pnl latest \
  --chain ethereum --address 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045 \
  --with-historical-breakdown
```

**Options:** `--chain`, `--address` (repeatable), `--min-liquidity`, `--with-historical-breakdown`,  `--body`

##### Historical PnL

```bash
# Historical Wallet profit and loss
allium realtime pnl history \
  --chain ethereum \
  --address 0x3c96937a5bce135c47133702d54b652498e5e375 \
  --start-timestamp 2024-03-01T00:00:00Z \
  --end-timestamp 2026-03-21T00:00:00Z \
  --min-liquidity 1000 \
  --granularity 1d
```

**Options:** `--chain`, `--address` (repeatable), `--granularity`, `--min-liquidity`, `--body`

---

### `allium explorer` -- SQL Query Execution

Run SQL queries on Allium's data warehouse. By default, the CLI polls silently and prints results. Use `-v` for progress details.

```bash
# Execute ad-hoc SQL (requires x402 or Tempo auth)
allium explorer run-sql "SELECT chain, COUNT(*) FROM crosschain.dex.trades GROUP BY chain LIMIT 10"

# Execute SQL from a file
allium explorer run-sql query.sql --limit 1000

# Run a saved query by ID with parameters
allium explorer run abc123 --param start_date=2026-01-01 --param chain=ethereum

# Just get the run ID without waiting
allium explorer run-sql "SELECT 1" --no-wait

# Check status of a query run
allium explorer status <run_id>

# Fetch results of a completed run
allium explorer results <run_id>

# Pipe CSV output directly
allium --format csv explorer run-sql "SELECT 1" > output.csv
```

| Command | Description |
|---|---|
| `run-sql <SQL_OR_FILE>` | Execute ad-hoc SQL (x402/Tempo auth required) |
| `run <QUERY_ID>` | Execute a saved Explorer query by ID |
| `status <RUN_ID>` | Check query run status (created, running, success, failed, canceled) |
| `results <RUN_ID>` | Download results of a completed run |

**Options:** `--limit`, `--no-wait`, `--param key=value` (repeatable), `--compute-profile`

---

### `allium mp` -- Machine Payment Tracking

Track costs for x402 and Tempo micropayment API calls. Payments are logged automatically to `~/.config/allium/cost_log.csv`.

```bash
# Total spend summary grouped by method and network
allium mp cost

# Full itemized payment history
allium mp cost list

# Export as CSV
allium --format csv mp cost list

# Clear the cost log
allium mp cost clear
```

| Command | Description |
|---|---|
| `mp cost` | Total spend summary (grouped by method/network with call counts) |
| `mp cost list` | Full itemized history with per-row details |
| `mp cost clear` | Delete the cost log (with confirmation prompt) |

---

### `allium auth` -- Authentication Management

```bash
# Interactive setup wizard (arrow-key selection)
allium auth setup

# Non-interactive setup (for scripts/CI)
allium auth setup --method api_key --api-key sk-...
allium auth setup --method tempo --private-key 0x... --chain-id 4217

# List all configured profiles
allium auth list

# Switch active profile
allium auth use <name>

# Delete a profile
allium auth remove <name>
```

## JSON Body Override

All realtime commands support a `--body` flag that accepts either inline JSON or a path to a `.json` file. When provided, it overrides all other options:

```bash
# Inline JSON
allium realtime prices latest --body '[{"chain":"solana","token_address":"So111..."}]'

# From file
allium realtime prices latest --body tokens.json
```

## Shell Completions

Tab-completion is available for all commands, subcommands, and options. Add one of the following to your shell config:

```bash
# Bash — add to ~/.bashrc
eval "$(_ALLIUM_COMPLETE=bash_source allium)"

# Zsh — add to ~/.zshrc
eval "$(_ALLIUM_COMPLETE=zsh_source allium)"

# Fish — add to ~/.config/fish/config.fish
_ALLIUM_COMPLETE=fish_source allium | source
```

Reload your shell to activate completions.

## Documentation

Full API documentation: [docs.allium.so](https://docs.allium.so)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and release instructions.
