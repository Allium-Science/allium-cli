from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field

from cli.constants.api import DEFAULT_AGENTS_URL, DEFAULT_API_URL
from cli.types.enums import TargetNetwork, TempoChainId


class ApiKeyProfile(BaseModel):
    method: Literal["api_key"] = "api_key"
    base_url: str = DEFAULT_API_URL
    api_key: str


class X402KeyProfile(BaseModel):
    method: Literal["x402_key"] = "x402_key"
    base_url: str = DEFAULT_AGENTS_URL
    private_key: str
    target_network: TargetNetwork


class X402PrivyProfile(BaseModel):
    method: Literal["x402_privy"] = "x402_privy"
    base_url: str = DEFAULT_AGENTS_URL
    privy_app_id: str
    privy_app_secret: str
    privy_wallet_id: str
    target_network: TargetNetwork


class TempoProfile(BaseModel):
    method: Literal["tempo"] = "tempo"
    base_url: str = DEFAULT_AGENTS_URL
    private_key: str
    chain_id: TempoChainId


Profile = Annotated[
    ApiKeyProfile | X402KeyProfile | X402PrivyProfile | TempoProfile,
    Field(discriminator="method"),
]

ProfileUnion = ApiKeyProfile | X402KeyProfile | X402PrivyProfile | TempoProfile
