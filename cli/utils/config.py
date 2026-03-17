from __future__ import annotations

import os
import stat
import tomllib
from pathlib import Path

import tomli_w

from cli.constants.config import CONFIG_DIR, CONFIG_VERSION, CREDENTIALS_FILE
from cli.types.config import AlliumConfig
from cli.types.profiles import (
    ProfileUnion,
)


class ConfigManager:
    """manages CLI configuration and credential profiles."""

    def __init__(self, config_dir: Path | None = None) -> None:
        self.config_dir = config_dir or CONFIG_DIR
        self.credentials_file = (
            config_dir / "credentials.toml" if config_dir else CREDENTIALS_FILE
        )

    def _ensure_dir(self) -> None:
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def load(self) -> AlliumConfig:
        if not self.credentials_file.exists():
            return AlliumConfig()
        with open(self.credentials_file, "rb") as f:
            data = tomllib.load(f)
        data.setdefault("config_version", CONFIG_VERSION)
        data.setdefault("active", "")
        data.setdefault("profiles", {})
        return AlliumConfig.model_validate(data)

    def save(self, config: AlliumConfig) -> None:
        self._ensure_dir()
        with open(self.credentials_file, "wb") as f:
            tomli_w.dump(config.model_dump(), f)
        os.chmod(self.credentials_file, stat.S_IRUSR | stat.S_IWUSR)

    def list_profiles(self) -> dict[str, ProfileUnion]:
        return self.load().profiles

    def get_active_profile_name(self) -> str:
        return self.load().active

    def get_active_profile(self) -> ProfileUnion | None:
        config = self.load()
        if not config.active:
            return None
        return config.profiles.get(config.active)

    def get_profile(self, name: str) -> ProfileUnion | None:
        return self.load().profiles.get(name)

    def set_active_profile(self, name: str) -> None:
        config = self.load()
        if name not in config.profiles:
            raise ValueError(f"Profile '{name}' does not exist")
        config.active = name
        self.save(config)

    def add_profile(
        self,
        name: str,
        profile: ProfileUnion,
        *,
        set_active: bool = True,
    ) -> None:
        config = self.load()
        config.profiles[name] = profile
        if set_active or not config.active:
            config.active = name
        self.save(config)

    def remove_profile(self, name: str) -> None:
        config = self.load()
        if name not in config.profiles:
            raise ValueError(f"Profile '{name}' does not exist")
        del config.profiles[name]
        if config.active == name:
            config.active = next(iter(config.profiles), "")
        self.save(config)


config_manager = ConfigManager()
