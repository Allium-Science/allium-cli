from __future__ import annotations

import csv
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from cli.constants.config import (
    COST_LOG_FIELDNAMES,
    COST_LOG_FILE,
    USDC_DECIMALS,
)


def _to_human_amount(raw_amount: str | int, decimals: int = USDC_DECIMALS) -> str:
    """convert a raw integer amount to a human-readable decimal string."""
    try:
        raw = int(raw_amount)
        value = Decimal(raw) / Decimal(10**decimals)
        return f"{value:.{decimals}f}"
    except (ValueError, TypeError):
        return str(raw_amount)


class CostLog:
    """persistent CSV log of micropayment costs."""

    def __init__(self, log_file: Path | None = None) -> None:
        self.log_file = log_file or COST_LOG_FILE

    def _ensure_dir(self) -> None:
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def log_payment(
        self,
        *,
        method: str,
        endpoint: str,
        network: str,
        raw_amount: str | int,
        token: str,
        wallet: str,
        http_status: int,
        decimals: int = USDC_DECIMALS,
    ) -> None:
        """append a payment record to the cost log."""
        self._ensure_dir()
        file_exists = self.log_file.exists()
        with open(self.log_file, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=COST_LOG_FIELDNAMES)
            if not file_exists:
                writer.writeheader()
            writer.writerow(
                {
                    "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
                    "method": method,
                    "endpoint": endpoint,
                    "network": network,
                    "amount": _to_human_amount(raw_amount, decimals),
                    "token": token,
                    "wallet": wallet,
                    "http_status": str(http_status),
                }
            )

    def read(self, limit: int | None = None) -> list[dict[str, str]]:
        """read rows from the cost log; returns last N if limit is set."""
        if not self.log_file.exists():
            return []
        with open(self.log_file, newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        if limit is not None:
            rows = rows[-limit:]
        return rows

    def total(self) -> dict[str, dict[str, Any]]:
        """sum amounts grouped by (method, network)."""
        rows = self.read()
        totals: dict[str, dict[str, Any]] = {}
        for row in rows:
            key = f"{row['method']}:{row['network']}"
            if key not in totals:
                totals[key] = {"amount": Decimal("0"), "calls": 0}
            try:
                totals[key]["amount"] += Decimal(row["amount"])
            except (ValueError, ArithmeticError):
                pass
            totals[key]["calls"] += 1
        return totals

    def clear(self) -> bool:
        """delete the cost log file. returns true if it existed."""
        if self.log_file.exists():
            self.log_file.unlink()
            return True
        return False


cost_log = CostLog()
