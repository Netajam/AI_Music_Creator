""""Is this the code that produced this take?"

The manifest already recorded the command, the preset, the lyrics and the
parameters — but not the version of the code that interpreted them. Hence a
diverging render at identical preset and seed, when generation had changed in
between. The goal is not to version the repo: it is to be able to answer that
one question.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path
from typing import Any

from aimc.workspace import ENGINE_ROOT, PACKAGE_ROOT, REPO_ROOT

GIT_TIMEOUT = 30


def local_modules() -> dict[str, str]:
    """sha256 of the currently loaded modules of our own, by relative path.

    We list what actually took part rather than the whole package: the reference
    tools do not influence a render, and including them would set the
    non-reproducibility warning blinking for nothing. `engine/` is excluded — it
    is an upstream clone, identified by its git revision.

    The keys are relative to the repo root (`aimc/generation/engine.py`) and not
    plain filenames: two modules can both be called `manifest.py` in two
    different domains.
    """
    found: dict[str, str] = {}
    for module in list(sys.modules.values()):
        raw = getattr(module, "__file__", None)
        if not raw:
            continue
        try:
            f = Path(raw).resolve()
        except OSError:
            continue
        if f.suffix != ".py" or not f.is_relative_to(PACKAGE_ROOT):
            continue
        try:
            found[str(f.relative_to(REPO_ROOT))] = hashlib.sha256(
                f.read_bytes()).hexdigest()
        except OSError:
            continue
    return dict(sorted(found.items()))


def _git(*rest: str) -> str | None:
    """Output of a git command in `engine/`, or None if the command fails."""
    try:
        res = subprocess.run(["git", "-C", str(ENGINE_ROOT), *rest],
                             capture_output=True, text=True, timeout=GIT_TIMEOUT)
    except (OSError, subprocess.SubprocessError):
        return None
    return res.stdout.strip() if res.returncode == 0 else None


def engine_revision() -> dict[str, Any] | None:
    """The revision of `engine/` as it is being used — read, never managed.

    `engine/` is an upstream ACE-Step clone: we do not modify it, we identify
    it. The cleanliness check only looks at `acestep/`, the code that influences
    a render: a `git status` over the whole folder would walk the eleven
    gigabytes of `checkpoints/`.
    """
    if not (ENGINE_ROOT / ".git").exists():
        return None
    head = _git("rev-parse", "HEAD")
    if head is None:
        return None
    dirty = _git("status", "--porcelain", "--", "acestep")
    return {"commit": head, "dirty": bool(dirty)}


def code_fingerprint() -> dict[str, Any]:
    """What it takes to answer "is this the code that produced this take?"."""
    # No global digest: generation and the studio do not load the same modules,
    # so two whole-set digests could never coincide. Such a field would only
    # have invited the comparison that does not work.
    return {"modules": local_modules(), "engine": engine_revision()}


def changed_modules(recorded: dict[str, str]) -> list[str]:
    """Modules recorded at render time whose file no longer says the same thing."""
    out = []
    for name, digest in sorted(recorded.items()):
        f = REPO_ROOT / name
        if not f.is_file():
            out.append(f"{name} no longer exists")
            continue
        try:
            now = hashlib.sha256(f.read_bytes()).hexdigest()
        except OSError:
            out.append(f"{name} is unreadable")
            continue
        if now != digest:
            out.append(f"{name} has changed since")
    return out


def engine_moved(recorded: dict[str, Any] | None) -> list[str]:
    """What has moved on the `engine/` side since the render."""
    current = engine_revision()
    if not recorded:
        return []
    if current and recorded.get("commit") != current.get("commit"):
        return [f"engine/ moved from {recorded['commit'][:7]} "
                f"to {current['commit'][:7]}"]
    if recorded.get("dirty"):
        return ["engine/ had local modifications at render time"]
    return []


def compare_code(recorded: dict[str, Any] | None) -> dict[str, Any]:
    """"Is this the code that produced this take?"

    We do not compare two whole-set digests: generation and the studio do not
    load the same modules, and their fingerprints could never coincide. So we
    take the modules *recorded at render time* and look at what those same files
    contain today.

    `match` is `None` when the question cannot be settled — a take with no
    manifest, or a manifest predating version tracking. Answering "no" would be
    as wrong as answering "yes", and the "regenerate lossless" shortcut relies on
    this so as not to promise an exact reproduction it cannot deliver.
    """
    if not recorded or not recorded.get("modules"):
        return {"match": None, "differences": [],
                "why": "this take does not record the version of the code that produced it"}
    differences = (changed_modules(recorded["modules"])
                   + engine_moved(recorded.get("engine")))
    return {"match": not differences, "differences": differences, "why": None}
