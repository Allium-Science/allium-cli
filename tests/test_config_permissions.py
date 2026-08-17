from __future__ import annotations

import os
import stat

import pytest

from cli.types import AlliumConfig, ApiKeyProfile
from cli.utils.config import ConfigManager


@pytest.fixture()
def mgr(tmp_path):
    """Return a ConfigManager pointed at a temp directory."""
    return ConfigManager(config_dir=tmp_path)


class TestCredentialsFilePermissions:
    def test_file_is_created_restricted_even_if_the_chmod_safety_net_never_runs(
        self, mgr, tmp_path, monkeypatch
    ):
        """credentials.toml holds raw private keys / API secrets. If the
        process is killed between file creation and a trailing chmod() call,
        a file created with default (umask-controlled) permissions is left
        world/group-readable *permanently*. The file must be created
        restricted from the moment it exists -- not rely on chmod as the
        only guard. We simulate "chmod never gets to run" directly instead
        of racing a real kill signal.
        """
        monkeypatch.setattr("cli.utils.config.os.chmod", lambda *a, **k: None)

        # a permissive umask is the normal case on most systems and is the
        # condition under which the bug reproduces.
        old_umask = os.umask(0o022)
        try:
            profile = ApiKeyProfile(api_key="sk-secret")
            config = AlliumConfig(active="default", profiles={"default": profile})
            mgr.save(config)
        finally:
            os.umask(old_umask)

        mode = stat.S_IMODE(os.stat(tmp_path / "credentials.toml").st_mode)
        assert mode == stat.S_IRUSR | stat.S_IWUSR, (
            f"credentials.toml has mode {oct(mode)}, expected 0600 "
            "(owner read/write only) even with the chmod() safety net disabled"
        )
        assert not mode & stat.S_IRWXG, "group must not have any access"
        assert not mode & stat.S_IRWXO, "other must not have any access"

    def test_preexisting_loosely_permissioned_file_gets_locked_down(
        self, mgr, tmp_path
    ):
        """upgrading from a version that created the file insecurely: the
        next save() must correct the permissions, not just leave them.
        """
        creds = tmp_path / "credentials.toml"
        creds.parent.mkdir(parents=True, exist_ok=True)
        creds.write_text("")
        os.chmod(creds, 0o644)

        mgr.save(AlliumConfig(active="x", profiles={"x": ApiKeyProfile(api_key="k")}))

        mode = stat.S_IMODE(os.stat(creds).st_mode)
        assert mode == stat.S_IRUSR | stat.S_IWUSR
