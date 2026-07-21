from pathlib import Path

import pytest

from sovereignaiswarm.config import (
    CloudForbiddenError,
    KillSwitchError,
    SovereignConfig,
    load_config,
)


def test_default_config_blocks_cloud_and_allows_local():
    cfg = SovereignConfig()
    assert cfg.is_local_url("http://127.0.0.1:11434/v1")
    assert cfg.is_local_url("http://localhost:11434/v1")
    assert cfg.is_local_url("http://host.docker.internal:11434/v1")
    assert not cfg.is_local_url("https://api.cloud-llm.example/v1")

    cfg.assert_llm_allowed("http://127.0.0.1:11434/v1")
    with pytest.raises(CloudForbiddenError):
        cfg.assert_llm_allowed("https://api.cloud-llm.example/v1")


def test_allow_cloud_permits_remote_url():
    cfg = SovereignConfig(allow_cloud=True)
    cfg.assert_llm_allowed("https://api.cloud-llm.example/v1")


def test_kill_switch_engaged_by_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    flag = tmp_path / ".kill_switch"
    cfg = SovereignConfig(kill_switch=True, kill_switch_path=str(flag))

    assert not cfg.kill_switch_engaged()
    cfg.assert_not_killed()

    flag.write_text("stop\n", encoding="utf-8")
    assert cfg.kill_switch_engaged()
    with pytest.raises(KillSwitchError):
        cfg.assert_not_killed()


def test_kill_switch_disabled_ignores_file(tmp_path):
    flag = tmp_path / ".kill_switch"
    flag.write_text("stop\n", encoding="utf-8")
    cfg = SovereignConfig(kill_switch=False, kill_switch_path=str(flag))
    assert not cfg.kill_switch_engaged()
    cfg.assert_not_killed()


def test_load_config_from_yaml_and_env(tmp_path, monkeypatch):
    path = tmp_path / "sovereign.yaml"
    path.write_text(
        "\n".join(
            [
                "allow_cloud: false",
                "kill_switch: true",
                "kill_switch_path: .kill_switch",
                "default_model: mistral",
                "llm_base_url: http://127.0.0.1:11434/v1",
                "max_turns: 7",
                "allowed_roots:",
                "  - ./data",
                "  - /tmp/swarm",
                "redact_patterns:",
                r'  - "sk-[A-Za-z0-9]+"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("SOVEREIGN_ALLOW_CLOUD", raising=False)
    monkeypatch.delenv("SWARM_LLM_MODEL", raising=False)
    monkeypatch.setenv("SOVEREIGN_MAX_TURNS", "3")

    cfg = load_config(path)
    assert cfg.default_model == "mistral"
    assert cfg.max_turns == 3  # env wins
    assert cfg.allowed_roots == ["./data", "/tmp/swarm"]
    assert cfg.redact("token sk-abc123 end") == "token [REDACTED] end"


def test_resolved_roots_are_absolute(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "workspace").mkdir()
    cfg = SovereignConfig(allowed_roots=["./workspace"])
    roots = cfg.resolved_roots()
    assert roots == [tmp_path.resolve() / "workspace"]


def test_private_lan_hosts_count_as_local():
    cfg = SovereignConfig()
    assert cfg.is_local_url("http://10.0.0.5:11434/v1")
    assert cfg.is_local_url("http://192.168.1.10:11434/v1")
    assert cfg.is_local_url("http://172.16.0.2:11434/v1")
    assert not cfg.is_local_url("http://172.15.0.2:11434/v1")
