"""Translating command-line arguments into parameters for the engine.

One mode per function. When it all lived in a single block, you had to follow
four branches and a couple of dozen conditional assignments to know what
`--lego` really changed.

The engine's classes are imported inside the functions: importing `acestep`
loads torch, and nothing that comes before generation should pay for it.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
from pathlib import Path
from typing import Any

from aimc.audio import duration as probe_duration

# Options that copy straight across onto the engine's parameters, when they are
# set. On the left the engine's attribute, on the right the one on args.
DIRECT_OVERRIDES = (
    ("lm_temperature", "lm_temperature"),
    ("lm_top_p", "lm_top_p"),
    ("lm_cfg_scale", "lm_cfg"),
    ("lm_negative_prompt", "negative"),
    ("sampler_mode", "sampler"),
    ("infer_method", "infer_method"),
    ("shift", "shift"),
    ("fade_in_duration", "fade_in"),
    ("fade_out_duration", "fade_out"),
    ("normalization_db", "normalize_db"),
)

# Beyond this gap, the requested duration no longer describes the source we are
# adding to.
DURATION_SLACK = 0.5


def task_type(args: argparse.Namespace) -> str:
    """The engine's mode, inferred from the option that was given."""
    if args.repaint:
        return "repaint"
    if args.lego:
        return "lego"
    if args.cover:
        return "cover"
    return "text2music"


def _apply_reference(params: Any, args: argparse.Namespace) -> None:
    """--reference conditions a NEW track; --cover re-records the source."""
    if args.reference:
        params.reference_audio = str(Path(args.reference).expanduser())
    if args.cover:
        params.src_audio = str(Path(args.cover).expanduser())
    if args.style_strength is not None:
        params.audio_cover_strength = args.style_strength


def _apply_repaint(params: Any, args: argparse.Namespace) -> None:
    """The track to touch up becomes the source, plus the interval targeted."""
    if not args.repaint:
        return
    params.src_audio = str(Path(args.repaint).expanduser())
    if args.repaint_from is not None:
        params.repainting_start = args.repaint_from
    if args.repaint_to is not None:
        params.repainting_end = args.repaint_to
    if args.repaint_mode is not None:
        params.repaint_mode = args.repaint_mode
    if args.repaint_strength is not None:
        params.repaint_strength = args.repaint_strength


def _apply_lego(params: Any, args: argparse.Namespace,
                instruction_for: Callable[[str, str], str]) -> None:
    """The requested track is generated over the source, which serves as context.

    The duration is necessarily the source's — a mismatch would generate the
    track over a length that corresponds to nothing.
    """
    if not args.lego:
        return
    source = Path(args.lego).expanduser()
    params.src_audio = str(source)
    params.instruction = instruction_for("lego", args.lego_track)
    if args.lego_from is not None:
        params.repainting_start = args.lego_from
    if args.lego_to is not None:
        params.repainting_end = args.lego_to

    source_duration = probe_duration(source)
    if source_duration and abs(source_duration - (args.duration or -1)) > DURATION_SLACK:
        print(f"Duration aligned to the source: {source_duration:g} s "
              f"(instead of {args.duration:g} s)" if args.duration
              else f"Duration aligned to the source: {source_duration:g} s")
        params.duration = source_duration


def _apply_retake(params: Any, args: argparse.Namespace) -> None:
    if args.retake_seed is not None:
        params.retake_seed = args.retake_seed
    if args.retake_variance is not None:
        params.retake_variance = args.retake_variance


def _apply_overrides(params: Any, args: argparse.Namespace) -> None:
    for attr, source in DIRECT_OVERRIDES:
        value = getattr(args, source)
        if value is not None:
            setattr(params, attr, value)
    if args.no_normalize:
        params.enable_normalization = False


def build_params(args: argparse.Namespace, lyrics: str,
                 instruction_for: Callable[[str, str], str]) -> Any:
    """The generation parameters, mode by mode."""
    from acestep.inference import GenerationParams

    params = GenerationParams(
        task_type=task_type(args),
        caption=args.style or "",
        lyrics=lyrics,
        instrumental=args.instrumental,
        vocal_language=args.language,
        bpm=args.bpm,
        keyscale=args.key or "",
        timesignature=args.time_signature or "",
        duration=args.duration if args.duration is not None else -1.0,
        inference_steps=args.steps,
        seed=args.seed,
        thinking=not args.no_thinking,
    )
    # The engine resolves dcw_enabled=None to "on for turbo models", which is
    # every model this repo uses. Saying False is the only way to say off, and
    # it is worth having a way: DCW runs a wavelet transform over the latents at
    # every step, and on a pre-Ampere card — where the engine has already fallen
    # back from bfloat16 to float16 — that is a plausible place for the range to
    # give out. Leaving it None keeps the engine's own default.
    if args.no_dcw:
        params.dcw_enabled = False
    _apply_reference(params, args)
    _apply_repaint(params, args)
    _apply_lego(params, args, instruction_for)
    _apply_retake(params, args)
    _apply_overrides(params, args)
    return params


def build_config(args: argparse.Namespace) -> Any:
    from acestep.inference import GenerationConfig

    return GenerationConfig(
        batch_size=args.count,
        audio_format=args.format,
        use_random_seed=args.seed < 0,
        seeds=None if args.seed < 0 else [args.seed],
    )
