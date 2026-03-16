from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field, model_validator

from cli.constants.config import CONFIG_VERSION
from cli.types.profiles import (
    ApiKeyProfile,
    TempoProfile,
    X402KeyProfile,
    X402PrivyProfile,
)


class AlliumConfig(BaseModel):
    config_version: int = CONFIG_VERSION
    active: str = ""
    profiles: dict[
        str,
        Annotated[
            ApiKeyProfile | X402KeyProfile | X402PrivyProfile | TempoProfile,
            Field(discriminator="method"),
        ],
    ] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_active(self) -> AlliumConfig:
        if self.active and self.active not in self.profiles:
            raise ValueError(
                f"Active profile '{self.active}' does not exist in profiles"
            )
        return self
