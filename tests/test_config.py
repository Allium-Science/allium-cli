from __future__ import annotations

import tomllib

import pytest

from cli.types import AlliumConfig, ApiKeyProfile, TempoChainId, TempoProfile
from cli.utils.config import ConfigManager


@pytest.fixture()
def mgr(tmp_path):
    """Return a ConfigManager pointed at a temp directory."""
    return ConfigManager(config_dir=tmp_path)


class TestLoadSave:
    def test_load_missing_file_returns_default(self, mgr):
        config = mgr.load()
        assert config.active == ""
        assert config.profiles == {}

    def test_save_and_load_roundtrip(self, mgr):
        profile = ApiKeyProfile(api_key="sk-test123")
        config = AlliumConfig(active="default", profiles={"default": profile})
        mgr.save(config)
        loaded = mgr.load()
        assert loaded.active == "default"
        assert loaded.profiles["default"].api_key == "sk-test123"

    def test_save_writes_config_version(self, mgr, tmp_path):
        mgr.save(AlliumConfig())
        raw = tomllib.loads((tmp_path / "credentials.toml").read_text())
        assert raw["config_version"] == 1

    def test_load_old_config_without_version(self, mgr, tmp_path):
        (tmp_path / "credentials.toml").write_text('active = ""\n\n[profiles]\n')
        config = mgr.load()
        assert config.config_version == 1


class TestProfileCRUD:
    def test_add_and_list(self, mgr):
        mgr.add_profile("mykey", ApiKeyProfile(api_key="sk-1"))
        profiles = mgr.list_profiles()
        assert "mykey" in profiles
        assert profiles["mykey"].api_key == "sk-1"

    def test_add_sets_active_by_default(self, mgr):
        mgr.add_profile("first", ApiKeyProfile(api_key="sk-1"))
        assert mgr.get_active_profile_name() == "first"

    def test_add_no_active(self, mgr):
        mgr.add_profile("first", ApiKeyProfile(api_key="sk-1"))
        mgr.add_profile("second", ApiKeyProfile(api_key="sk-2"), set_active=False)
        assert mgr.get_active_profile_name() == "first"

    def test_get_profile(self, mgr):
        mgr.add_profile("x", ApiKeyProfile(api_key="sk-x"))
        assert mgr.get_profile("x") is not None
        assert mgr.get_profile("nonexistent") is None

    def test_get_active_profile_none_when_empty(self, mgr):
        assert mgr.get_active_profile() is None

    def test_set_active_profile(self, mgr):
        mgr.add_profile("a", ApiKeyProfile(api_key="sk-a"))
        mgr.add_profile("b", ApiKeyProfile(api_key="sk-b"))
        mgr.set_active_profile("a")
        assert mgr.get_active_profile_name() == "a"

    def test_set_active_profile_missing_raises(self, mgr):
        with pytest.raises(ValueError, match="does not exist"):
            mgr.set_active_profile("ghost")

    def test_remove_profile(self, mgr):
        mgr.add_profile("rm_me", ApiKeyProfile(api_key="sk-rm"))
        mgr.remove_profile("rm_me")
        assert "rm_me" not in mgr.list_profiles()

    def test_remove_active_rotates(self, mgr):
        mgr.add_profile("a", ApiKeyProfile(api_key="sk-a"))
        mgr.add_profile("b", ApiKeyProfile(api_key="sk-b"))
        mgr.set_active_profile("a")
        mgr.remove_profile("a")
        assert mgr.get_active_profile_name() == "b"

    def test_remove_missing_raises(self, mgr):
        with pytest.raises(ValueError, match="does not exist"):
            mgr.remove_profile("nope")

    def test_multiple_profile_types(self, mgr):
        mgr.add_profile("key", ApiKeyProfile(api_key="sk-1"))
        mgr.add_profile(
            "tempo",
            TempoProfile(private_key="0xabc", chain_id=TempoChainId.MAINNET),
        )
        profiles = mgr.list_profiles()
        assert isinstance(profiles["key"], ApiKeyProfile)
        assert isinstance(profiles["tempo"], TempoProfile)
