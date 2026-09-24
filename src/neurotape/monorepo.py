"""Where the shared tools live: the polarizetech `audio-projects` monorepo, a SEPARATE checkout.

sim-neural-memory was split out of that monorepo (projects/neurotape, 2026-09-24) and still uses its shared
infrastructure rather than copying it. Two things are used in code:

  tools/result-provenance                 stamps every results folder (provenance.json)
  tools/universal-wave-translation-layer  `uwtl.surrogates.iaaft`, the secondary null for best-lag recall

The rule, from the monorepo's own split-out repos: RESOLVE, OR RAISE WITH THE LINE THAT WOULD RESOLVE IT. A
candidate is accepted only if it carries the marker `tools/REGISTRY.md` -- a directory that merely exists is
not the monorepo. Nothing here guesses, copies a tool, or falls back to a local reimplementation.

Search order: $NEUROTAPE_MONOREPO, then a sibling `audio-projects` next to this repo, then ~/Sites/audio-projects.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

MARKER = Path("tools") / "REGISTRY.md"
REPO_ROOT = Path(__file__).resolve().parents[2]
CLONE = "git clone --recurse-submodules https://github.com/polarizetech/audio-projects.git"


class MonorepoNotFound(RuntimeError):
    pass


def _candidates() -> list[Path]:
    out = []
    if os.environ.get("NEUROTAPE_MONOREPO"):
        out.append(Path(os.environ["NEUROTAPE_MONOREPO"]).expanduser())
    out += [REPO_ROOT.parent / "audio-projects", Path.home() / "Sites" / "audio-projects"]
    return out


def root() -> Path:
    tried = []
    for c in _candidates():
        c = c.resolve()
        if (c / MARKER).is_file():
            return c
        tried.append(str(c))
    raise MonorepoNotFound(
        "the audio-projects monorepo (shared tools) was not found; looked for tools/REGISTRY.md under: "
        + ", ".join(tried) + f".\n  Clone it beside this repo:  cd {REPO_ROOT.parent} && {CLONE}\n"
        "  or point at an existing checkout:  export NEUROTAPE_MONOREPO=/path/to/audio-projects")


def tool(name: str) -> Path:
    p = root() / "tools" / name
    if not p.is_dir() or not any(p.iterdir()):
        raise MonorepoNotFound(f"monorepo tool {name!r} is missing or empty at {p} (a submodule not initialised?).\n"
                               f"  cd {root()} && git submodule update --init tools/{name}")
    return p


def import_uwtl():
    """`uwtl`, installed or from the monorepo's submodule -- never two copies."""
    try:
        import uwtl
        return uwtl
    except ImportError:
        pass
    src = tool("universal-wave-translation-layer") / "src"
    if not (src / "uwtl").is_dir():
        raise MonorepoNotFound(f"no uwtl package under {src}")
    sys.path.insert(0, str(src))
    import uwtl
    return uwtl


def provenance_module():
    p = str(tool("result-provenance"))
    if p not in sys.path:
        sys.path.insert(0, p)
    import provenance
    return provenance


def stamp(dependencies: list[str]) -> dict:
    """The monorepo's provenance stamp for the shared tools a result used, plus THIS repo's own commit -- the
    monorepo stamp alone records the monorepo's HEAD, which says nothing about the code that ran here."""
    import subprocess

    def git(*a):
        r = subprocess.run(["git", *a], cwd=str(REPO_ROOT), capture_output=True, text=True)
        return r.stdout.strip() if r.returncode == 0 else None
    s = provenance_module().stamp(dependencies)
    s["monorepo_head"] = s.pop("head", None)
    s["repo"] = dict(name="sim-neural-memory", sha=git("rev-parse", "HEAD"), dirty=bool(git("status", "--porcelain")))
    return s
