from __future__ import annotations

from enum import StrEnum


class AuthMethod(StrEnum):
    API_KEY = "api_key"
    X402_KEY = "x402_key"
    X402_PRIVY = "x402_privy"
    TEMPO = "tempo"


class TargetNetwork(StrEnum):
    BASE_MAINNET = "eip155:8453"

    @property
    def label(self) -> str:
        return _NETWORK_LABELS[self]


_NETWORK_LABELS: dict[TargetNetwork, str] = {
    TargetNetwork.BASE_MAINNET: "Base Mainnet",
}


class TempoChainId(StrEnum):
    MAINNET = "4217"

    @property
    def label(self) -> str:
        return _TEMPO_LABELS[self]


_TEMPO_LABELS: dict[TempoChainId, str] = {
    TempoChainId.MAINNET: "Tempo Mainnet",
}


class OutputFormat(StrEnum):
    JSON = "json"
    TABLE = "table"
    CSV = "csv"


class TimeGranularity(StrEnum):
    FIFTEEN_SEC = "15s"
    ONE_MIN = "1m"
    FIVE_MIN = "5m"
    ONE_HOUR = "1h"
    ONE_DAY = "1d"


class TokenSortField(StrEnum):
    VOLUME = "volume"
    TRADE_COUNT = "trade_count"
    FDV = "fully_diluted_valuation"
    ADDRESS = "address"
    NAME = "name"
