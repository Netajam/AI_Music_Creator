"""What a derived take carries over from the take it came from."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from aimc.provenance import manifest_for

# Tempo, key and time signature: without them the added track does not lock onto
# the grid of the track it is supposed to accompany. For each one: the
# command-line option, the field in the source manifest, and what counts as
# "not set".
#
# `bpm` is tested against None and not against falsiness, unlike the other two:
# a preset that writes 0 must stay a 0 that validation rejects, rather than
# being quietly replaced by the source's tempo.
GRID_FIELDS: tuple[tuple[str, str, Callable[[Any], bool]], ...] = (
    ("bpm", "bpm", lambda v: v is None),
    ("key", "keyscale", lambda v: not v),
    ("time_signature", "timesignature", lambda v: not v),
)


def _source_manifest(audio: Path) -> dict[str, Any] | None:
    """The source take's manifest, or None if it has no usable one."""
    manifest = manifest_for(audio)
    if manifest is None:
        return None
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return data if isinstance(data, dict) else None


def _inherit_lyrics(args: argparse.Namespace, data: dict[str, Any]) -> None:
    """The source's lyrics — or the admission that there are none."""
    if args.lyrics or args.lyrics_text or args.instrumental:
        return
    inherited = data.get("lyrics")
    if inherited:
        args.lyrics_text = inherited
    else:
        args.instrumental = True


def inherit_from_source(args: argparse.Namespace) -> None:
    """For --lego: carries style and lyrics over from the source take's manifest.

    Adding a guitar to a track means playing *inside* that track. Without the
    original style the model improvises a context that is not the one of the
    audio it is given, and the added part sounds beside it. The manifest written
    by the previous take contains exactly what is needed; whatever came from the
    command line or from a preset still takes priority.
    """
    if not args.lego:
        return
    data = _source_manifest(Path(args.lego).expanduser())
    if data is None:
        return

    src = data.get("params") or {}
    if not args.style:
        args.style = src.get("caption") or None
    for dest, field, is_unset in GRID_FIELDS:
        if is_unset(getattr(args, dest)) and src.get(field):
            setattr(args, dest, src[field])
    _inherit_lyrics(args, data)
