"""The settings file written next to each take."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from aimc.provenance import audio_fingerprint, code_fingerprint

# What reads back as-is from a JSON file. The engine's other attributes
# (tensors, handlers) have no place in a settings file.
SERIALISABLE = (str, int, float, bool, type(None), list)


def _public_fields(obj: Any, keep: tuple[type, ...] | None = None) -> dict[str, Any]:
    """An engine object's public attributes, filtered down to what serialises."""
    fields = {k: v for k, v in vars(obj).items() if not k.startswith("_")}
    if keep is None:
        return fields
    return {k: v for k, v in fields.items() if isinstance(v, keep)}


def write_manifest(target: Path, args: argparse.Namespace, params: Any, config: Any,
                   lyrics: str, device: str, backend: str) -> Path:
    """Write <track>.json: what it takes to remake or vary this exact take.

    The engine keeps nothing next to the audio (its own sidecar is a latent
    cache for repaint, fed by the Gradio interface only). Without this file, the
    settings of a successful take are lost the moment the script ends.

    Two fields answer questions the parameters alone cannot settle (see
    aimc/provenance/):

      * `fingerprint` identifies the *audio* produced. Without it, two different
        takes can carry the same name with nothing to say so.
      * `code` identifies the *version of the code* that interpreted those
        parameters. Without it, the promise "what it takes to remake this exact
        take" is false as soon as generation changes — and it has.
    """
    manifest = {
        "audio": target.name,
        "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
        # A protocol value, not a filename: the studio compares it against
        # "reconstructed" to tell an original manifest from a reconstructed one,
        # and it is already written to disk for every existing take. It does not
        # follow renames.
        "provenance": "song.py",
        "command": " ".join(sys.argv),
        "preset": args.preset,
        "lyrics_file": args.lyrics,
        "lyrics": lyrics,
        "device": device,
        "lm_backend": backend,
        "models": {"dit": args.dit, "lm": None if args.no_lm else args.lm,
                   "mlx_dit": bool(args.mlx_dit)},
        "params": _public_fields(params, SERIALISABLE),
        "config": _public_fields(config),
        "fingerprint": audio_fingerprint(target),
        "code": code_fingerprint(),
    }
    path = target.with_suffix(".json")
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return path
