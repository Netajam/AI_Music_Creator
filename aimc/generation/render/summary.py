"""The recap printed before launching — and everything `--dry-run` shows.

It is the last chance to notice that what is about to be generated is not what
you thought, before several minutes of computation.
"""

from __future__ import annotations

import argparse

from aimc.generation.catalog import LOSSY_FORMATS


def _bound(value: float | None) -> str:
    """The end of an interval: -1 and absence both mean "to the very end"."""
    return "end" if value in (None, -1) else f"{value:g} s"


def mode_line(args: argparse.Namespace) -> str:
    """What this command does, in one sentence."""
    if args.repaint:
        mode = (f"repaint of {args.repaint} "
                f"[{(args.repaint_from or 0):g} s -> {_bound(args.repaint_to)}]")
    elif args.lego:
        mode = (f"adding a {args.lego_track} track to {args.lego} "
                f"[{(args.lego_from or 0):g} s -> {_bound(args.lego_to)}]")
    elif args.cover:
        mode = f"cover of {args.cover}"
    elif args.reference:
        mode = f"new song in the style of {args.reference}"
    else:
        mode = "text -> music"
    if args.retake_seed is not None:
        mode += f" | variation on seed {args.retake_seed}"
    return mode


def _rows(args: argparse.Namespace, lyrics: str, device: str,
          backend: str) -> list[tuple[str, str]]:
    lossy_note = ("   (listening only: cannot be mastered)"
                  if args.format in LOSSY_FORMATS else "")
    return [
        ("mode", mode_line(args)),
        ("style", args.style or "(none)"),
        ("lyrics", "[instrumental]" if args.instrumental
                   else f"{len(lyrics)} characters, {len(lyrics.splitlines())} lines"),
        ("language", args.language),
        ("tempo", f"{args.bpm} BPM" if args.bpm else "auto"),
        ("key", args.key or "auto"),
        ("duration", f"{args.duration:g} s" if args.duration else "auto"),
        ("audio influence", f"{args.style_strength}"
                            if args.style_strength is not None else "n/a"),
        ("models", f"{args.dit} + {'no LM' if args.no_lm else args.lm}"),
        ("compute", f"{device} (LM: {backend}, DiT: "
                    f"{'MLX' if args.mlx_dit else 'PyTorch'})"),
        ("output", f"{args.count} × .{args.format} -> {args.out}" + lossy_note),
    ]


def describe(args: argparse.Namespace, lyrics: str, device: str, backend: str) -> None:
    lines = _rows(args, lyrics, device, backend)
    width = max(len(k) for k, _ in lines)
    print("\n  Generation settings")
    print("  " + "-" * (width + 40))
    for key, value in lines:
        print(f"  {key.rjust(width)} : {value}")
    print()
