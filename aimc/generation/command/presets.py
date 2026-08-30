"""A JSON preset supplies the default values; the command line wins."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Options whose value is a path: in a preset, they are relative to the preset
# itself, not to the current directory.
PATH_KEYS = {"lyrics", "reference", "cover"}


def _explicitly_set(parser: argparse.ArgumentParser) -> set[str]:
    """Return the dests of the options actually present in sys.argv."""
    seen: set[str] = set()
    for action in parser._actions:
        for opt in action.option_strings:
            for token in sys.argv[1:]:
                if token == opt or token.startswith(opt + "="):
                    seen.add(action.dest)
    return seen


def _resolve_path(value: str, preset_path: Path) -> str:
    """A preset path is read first next to the preset, then as-is."""
    candidate = (preset_path.parent / value).expanduser()
    return str(candidate if candidate.exists() else Path(value).expanduser())


def _load(preset_path: Path, parser: argparse.ArgumentParser) -> dict[str, object]:
    if not preset_path.is_file():
        parser.error(f"preset not found: {preset_path}")
    try:
        data = json.loads(preset_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        parser.error(f"invalid JSON preset ({preset_path}): {exc}")
    if not isinstance(data, dict):
        parser.error(f"the preset must contain a JSON object: {preset_path}")
    return data


def apply_preset(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    """Merge a JSON preset into args, without overriding what came from the CLI."""
    if not args.preset:
        return

    preset_path = Path(args.preset).expanduser()
    data = _load(preset_path, parser)

    # What was typed explicitly on the command line wins. We spot those options
    # by replaying the parser over empty default values.
    explicit = _explicitly_set(parser)

    for key, value in data.items():
        dest = key.replace("-", "_")
        if not hasattr(args, dest):
            parser.error(f"unknown key in preset: {key}")
        if dest in explicit:
            continue
        if dest in PATH_KEYS and isinstance(value, str):
            value = _resolve_path(value, preset_path)
        setattr(args, dest, value)
