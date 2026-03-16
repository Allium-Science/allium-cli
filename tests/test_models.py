from __future__ import annotations

import pytest
from pydantic import ValidationError

from cli.types import (
    AlliumConfig,
    ApiKeyProfile,
    AuthMethod,
    TargetNetwork,
    TempoChainId,
    TempoProfile,
    X402KeyProfile,
    method_label,
    network_label,
)


class TestProfileDiscriminatedUnion:
    def test_api_key_roundtrip(self):
        p = ApiKeyProfile(api_key="sk-test")
        assert p.method == "api_key"
        assert p.api_key == "sk-test"
        assert p.base_url == "https://api.allium.so"

    def test_x402_key_roundtrip(self):
        p = X402KeyProfile(
            private_key="0xabc", target_network=TargetNetwork.BASE_MAINNET
        )
        assert p.method == "x402_key"
        assert p.target_network == TargetNetwork.BASE_MAINNET

    def test_tempo_roundtrip(self):
        p = TempoProfile(private_key="0xabc", chain_id=TempoChainId.TESTNET)
        assert p.method == "tempo"
        assert p.chain_id == TempoChainId.TESTNET

    def test_discriminated_union_from_dict(self):
        config = AlliumConfig.model_validate(
            {
                "config_version": 1,
                "active": "mykey",
                "profiles": {
                    "mykey": {"method": "api_key", "api_key": "sk-test"},
                    "myx402": {
                        "method": "x402_key",
                        "private_key": "0x1",
                        "target_network": "eip155:8453",
                    },
                },
            }
        )
        assert isinstance(config.profiles["mykey"], ApiKeyProfile)
        assert isinstance(config.profiles["myx402"], X402KeyProfile)


class TestAlliumConfig:
    def test_empty_config(self):
        config = AlliumConfig()
        assert config.active == ""
        assert config.profiles == {}
        assert config.config_version == 1

    def test_active_must_exist_in_profiles(self):
        with pytest.raises(ValidationError, match="does not exist"):
            AlliumConfig(active="missing", profiles={})

    def test_defaults_version(self):
        config = AlliumConfig.model_validate({"active": "", "profiles": {}})
        assert config.config_version == 1


class TestLabels:
    def test_network_label_known(self):
        assert network_label("eip155:8453") == "Base Mainnet"

    def test_network_label_unknown_returns_id(self):
        assert network_label("unknown:999") == "unknown:999"

    def test_method_label_known(self):
        assert method_label("api_key") == "API Key"
        assert method_label("tempo") == "Tempo"

    def test_method_label_unknown_returns_id(self):
        assert method_label("some_new_method") == "some_new_method"


class TestEnums:
    def test_auth_method_values(self):
        assert set(AuthMethod) == {"api_key", "x402_key", "x402_privy", "tempo"}

    def test_target_network_label(self):
        assert TargetNetwork.BASE_MAINNET.label == "Base Mainnet"
        assert TargetNetwork.BASE_SEPOLIA.label == "Base Sepolia (Testnet)"

    def test_tempo_chain_id_label(self):
        assert TempoChainId.MAINNET.label == "Tempo Mainnet"
        assert TempoChainId.TESTNET.label == "Tempo Testnet"
