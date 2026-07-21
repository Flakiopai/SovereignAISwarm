from pathlib import Path

import pytest

from sovereignaiswarm.config import KillSwitchError, SovereignConfig
from sovereignaiswarm.filesystem import FilesystemError, FilesystemMutator


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    cfg = SovereignConfig(
        kill_switch=False,
        allowed_roots=["./workspace"],
    )
    return FilesystemMutator(config=cfg, base=tmp_path), workspace


def test_write_read_append_list(sandbox):
    fs, workspace = sandbox
    path = fs.write("workspace/note.txt", "hello")
    assert Path(path).read_text(encoding="utf-8") == "hello"
    assert fs.read("workspace/note.txt") == "hello"

    fs.append("workspace/note.txt", " world")
    assert fs.read("workspace/note.txt") == "hello world"
    assert "note.txt" in fs.list("workspace")


def test_blocks_path_traversal(sandbox):
    fs, _workspace = sandbox
    with pytest.raises(FilesystemError):
        fs.read("../secret.txt")
    with pytest.raises(FilesystemError):
        fs.write("/etc/passwd", "nope")


def test_blocks_outside_allowed_roots(sandbox, tmp_path):
    fs, _workspace = sandbox
    outside = tmp_path / "outside.txt"
    outside.write_text("x", encoding="utf-8")
    with pytest.raises(FilesystemError):
        fs.read(str(outside))


def test_delete_disabled_by_default(sandbox):
    fs, _workspace = sandbox
    fs.write("workspace/tmp.txt", "x")
    with pytest.raises(FilesystemError, match="Delete disabled"):
        fs.delete("workspace/tmp.txt")


def test_delete_when_enabled(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "workspace").mkdir()
    cfg = SovereignConfig(kill_switch=False, allowed_roots=["./workspace"])
    fs = FilesystemMutator(config=cfg, base=tmp_path, allow_delete=True)
    fs.write("workspace/tmp.txt", "x")
    deleted = fs.delete("workspace/tmp.txt")
    assert not Path(deleted).exists()


def test_kill_switch_blocks_io(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "workspace").mkdir()
    flag = tmp_path / ".kill_switch"
    flag.write_text("stop\n", encoding="utf-8")
    cfg = SovereignConfig(
        kill_switch=True,
        kill_switch_path=str(flag),
        allowed_roots=["./workspace"],
    )
    fs = FilesystemMutator(config=cfg, base=tmp_path)
    with pytest.raises(KillSwitchError):
        fs.write("workspace/x.txt", "nope")


def test_agent_tool_wrappers(sandbox):
    fs, _workspace = sandbox
    assert "Wrote" in fs.tool_write_file("workspace/a.txt", "hi")
    assert fs.tool_read_file("workspace/a.txt") == "hi"
    assert "a.txt" in fs.tool_list_dir("workspace")
