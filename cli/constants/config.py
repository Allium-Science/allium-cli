from __future__ import annotations

from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "allium"
CREDENTIALS_FILE = CONFIG_DIR / "credentials.toml"
CONFIG_VERSION = 1

COST_LOG_FILE = CONFIG_DIR / "cost_log.csv"
COST_LOG_FIELDNAMES = [
    "timestamp",
    "method",
    "endpoint",
    "network",
    "amount",
    "token",
    "wallet",
    "http_status",
]
USDC_DECIMALS = 6

EXIT_ERROR = 1
EXIT_AUTH = 3
