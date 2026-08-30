#!/usr/bin/env python3
"""Checks the domain stack in `aimc/` — what ruff and mypy do not see.

Three rules hold the architecture together, and all three break silently: the
code keeps running on the machine of whoever wrote it, and fails elsewhere, or
later, or only on the command that was not re-run.

  1. The domains stack. A domain only imports those below it, never one at the
     same level nor one above. That is what keeps the graph readable and what
     guarantees it stays acyclic.

  2. `./master`, `./grab` and `./blend-refs` run under the system python3, where
     numpy does not exist. The domains they cross must not import it — otherwise
     all three commands die at import time.

  3. `acestep` is only imported inside `generation/render/`, and inside a
     function. An import hoisted to the top of a module would load torch for a
     `--help`, and reserve several gigabytes just to print a help message.

Standard library only: this script runs before everything else.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent.parent / "aimc"

# From the base towards the top. A domain can only import ranks strictly lower
# than its own.
LAYERS: dict[str, int] = {
    "workspace": 0,
    "audio": 1,
    "provenance": 2, "analysis": 2, "mastering": 2, "references": 2,
    "generation": 3,
    "studio": 4,
}

# Domains crossed by the commands that run without `engine/.venv`.
NUMPY_FREE = {"workspace", "audio", "mastering", "references"}

# The only place the engine can be imported from.
ENGINE_HOME = "generation/render"


def domain_of(path: Path) -> str:
    """The domain this file belongs to: `audio`, `generation`, …"""
    rel = path.relative_to(PACKAGE)
    return rel.parts[0] if len(rel.parts) > 1 else rel.stem


def imported_domains(tree: ast.Module) -> set[str]:
    """The `aimc` domains this module names in its imports."""
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("aimc"):
            parts = (node.module or "").split(".")
            if len(parts) > 1:
                found.add(parts[1])
        elif isinstance(node, ast.Import):
            for alias in node.names:
                parts = alias.name.split(".")
                if parts[0] == "aimc" and len(parts) > 1:
                    found.add(parts[1])
    return found


def top_level_imports(tree: ast.Module) -> set[str]:
    """The modules imported at module level — not those deferred inside a function."""
    found: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            found.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module.split(".")[0])
    return found


def all_imports(tree: ast.Module) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module.split(".")[0])
    return found


def check(path: Path, tree: ast.Module) -> list[str]:
    rel = path.relative_to(PACKAGE.parent)
    domain = domain_of(path)
    rank = LAYERS.get(domain)
    problems = []

    for other in sorted(imported_domains(tree)):
        if other == domain or other not in LAYERS or rank is None:
            continue
        if LAYERS[other] >= rank:
            problems.append(
                f"{rel}: {domain} (rank {rank}) imports {other} "
                f"(rank {LAYERS[other]}) — a domain only knows those below it")

    if domain in NUMPY_FREE and "numpy" in all_imports(tree):
        problems.append(
            f"{rel}: {domain} imports numpy, but ./master, ./grab and "
            f"./blend-refs run under the system python3, without numpy")

    if "acestep" in all_imports(tree):
        if ENGINE_HOME not in rel.as_posix():
            problems.append(
                f"{rel}: only {ENGINE_HOME}/ imports acestep")
        elif "acestep" in top_level_imports(tree):
            problems.append(
                f"{rel}: acestep imported at module level — it has to be inside "
                f"a function, so that --help does not load torch")
    return problems


def main() -> int:
    problems: list[str] = []
    files = sorted(PACKAGE.rglob("*.py"))
    for path in files:
        problems += check(path, ast.parse(path.read_text(encoding="utf-8")))

    for problem in problems:
        print(f"  {problem}", file=sys.stderr)
    if problems:
        print(f"\n  {len(problems)} breach(es) of the domain stack.",
              file=sys.stderr)
        return 1
    print(f"{len(files)} files: the domain stack holds.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
