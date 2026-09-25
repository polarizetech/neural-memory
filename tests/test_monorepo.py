"""The monorepo lookup resolves or raises with the fix; it never falls back to a local copy."""
import pytest

from neurotape import monorepo


def _have_monorepo() -> bool:
    try:
        monorepo.root()
        return True
    except monorepo.MonorepoNotFound:
        return False


needs_monorepo = pytest.mark.skipif(not _have_monorepo(), reason="the private audio-projects monorepo is not checked out")


@needs_monorepo
def test_resolves_to_a_checkout_carrying_the_marker():
    assert (monorepo.root() / monorepo.MARKER).is_file()


def test_a_directory_without_the_marker_is_not_the_monorepo(tmp_path, monkeypatch):
    monkeypatch.setattr(monorepo, "_candidates", lambda: [tmp_path])
    with pytest.raises(monorepo.MonorepoNotFound, match="git clone"):
        monorepo.root()


@needs_monorepo
def test_a_missing_tool_raises_with_the_submodule_line():
    with pytest.raises(monorepo.MonorepoNotFound, match="submodule update"):
        monorepo.tool("no-such-tool")


@needs_monorepo
def test_the_shared_tools_this_repo_uses_resolve():
    assert (monorepo.tool("result-provenance") / "provenance.py").is_file()
    import importlib
    u = monorepo.import_uwtl()           # import the submodule: attribute access passed only if an earlier test had
    assert hasattr(importlib.import_module(u.__name__ + ".surrogates"), "iaaft")   # imported it (found 2026-09-24)
    s = monorepo.stamp(["tools/result-provenance"])
    assert s["repo"]["name"] == "sim-neural-memory" and "tools/result-provenance" in s["dependencies"]
