"""Refuse early what the engine would refuse late, or worse, accept wrongly.

All these checks run before the slightest heavy import: a typo should not cost
the loading of a 2-billion-parameter model. The order of the checks is the one
they are listed in at the bottom of the module, and the first one that fails
stops everything — the message we want to show is the one closest to the cause.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from aimc.generation.catalog import (
    BPM_RANGE,
    DURATION_RANGE,
    STYLE_MAX_CHARS,
    TRACK_NAMES,
)
from aimc.workspace import CHECKPOINT_DIR

# The four modes that take audio as input, with their option.
AUDIO_MODES = ("--reference", "--cover", "--repaint", "--lego")


def _audio_modes(args: argparse.Namespace) -> list[tuple[str, str | None]]:
    return [(flag, getattr(args, flag.lstrip("-").replace("-", "_")))
            for flag in AUDIO_MODES]


def _check_style(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    if not args.style and not args.cover and not args.lego:
        parser.error("--style is required (except in --cover and --lego modes, "
                     "where it is inferred from the source)")
    if args.style and len(args.style) > STYLE_MAX_CHARS:
        parser.error(f"--style is {len(args.style)} characters, "
                     f"the maximum is {STYLE_MAX_CHARS}")


def _check_exclusive_modes(args: argparse.Namespace,
                           parser: argparse.ArgumentParser) -> None:
    chosen = [flag for flag, value in _audio_modes(args) if value]
    if len(chosen) > 1:
        parser.error(f"{' and '.join(chosen)} are mutually exclusive: --reference "
                     "creates a new song in a similar style, --cover reworks the whole "
                     "track, --repaint regenerates only one section of it, and --lego "
                     "adds a track to it")


def _check_lego(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    if args.lego and not args.lego_track:
        parser.error("--lego needs --lego-track: which track should be added? "
                     + ", ".join(TRACK_NAMES))
    if not args.lego:
        for opt, value in (("--lego-track", args.lego_track),
                           ("--lego-from", args.lego_from), ("--lego-to", args.lego_to)):
            if value is not None:
                parser.error(f"{opt} only makes sense with --lego")
    _check_interval(parser, "--lego-from", args.lego_from, "--lego-to", args.lego_to)


def _check_audio_files(args: argparse.Namespace,
                       parser: argparse.ArgumentParser) -> None:
    for opt, value in _audio_modes(args):
        if value and not Path(value).expanduser().is_file():
            parser.error(f"audio file not found for {opt}: {value}")


def _check_repaint(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    if not args.repaint and (args.repaint_from is not None or args.repaint_to is not None):
        parser.error("--repaint-from / --repaint-to only make sense with --repaint")
    _check_interval(parser, "--repaint-from", args.repaint_from,
                    "--repaint-to", args.repaint_to)


def _check_interval(parser: argparse.ArgumentParser, start_opt: str,
                    start: float | None, end_opt: str, end: float | None) -> None:
    """An end before its start is a typo, not an intention.

    -1 is how the engine writes "to the very end": it is not a bound, and
    comparing it with the start would make no sense.
    """
    if start is None or end is None or end == -1:
        return
    if end <= start:
        parser.error(f"{end_opt} ({end}) must come after {start_opt} ({start})")


def _check_range(parser: argparse.ArgumentParser, opt: str, value: float | None,
                 lo: float, hi: float, unit: str = "") -> None:
    if value is not None and not lo <= value <= hi:
        parser.error(f"{opt} must be between {lo} and {hi}{unit} (got {value})")


def _check_ranges(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    _check_range(parser, "--retake-variance", args.retake_variance, 0.0, 1.0)
    _check_range(parser, "--lm-temperature", args.lm_temperature, 0.0, 2.0)
    _check_range(parser, "--bpm", args.bpm, *BPM_RANGE)
    _check_range(parser, "--duration", args.duration, *DURATION_RANGE, unit=" seconds")
    _check_range(parser, "--style-strength", args.style_strength, 0.0, 1.0)
    if args.count < 1:
        parser.error("--count must be at least 1")


def _check_models(_args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    if not CHECKPOINT_DIR.is_dir():
        parser.error(f"models missing: {CHECKPOINT_DIR}\n"
                     f"run this first:  cd engine && uv run acestep-download")


CHECKS = (_check_style, _check_exclusive_modes, _check_lego, _check_audio_files,
          _check_repaint, _check_ranges, _check_models)


def validate(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    for check in CHECKS:
        check(args, parser)
