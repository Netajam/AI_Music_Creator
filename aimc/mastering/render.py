"""The normalisation itself: the filter chain, and writing it out.

Two traps in `ffmpeg -af loudnorm` that this module works around:

  * the filter works internally at 192 kHz and **outputs at 192 kHz** unless
    `-ar` is forced: a master at 192 kHz is not what distributors expect;
  * `linear=true` in a single pass does not have the measured values and falls
    back to dynamic mode. You have to measure first, then feed the measurements
    back in.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aimc.mastering.targets import TARGET_LRA


@dataclass(frozen=True)
class RenderOptions:
    """What the user asked for on this output."""

    lufs: float
    true_peak: float
    head: float
    tail: float
    bits: int
    sample_rate: int
    flac: bool


def loudnorm_filter(opts: RenderOptions, stats: dict[str, Any]) -> str:
    """The second pass: the first pass's measurements are fed back into it.

    That is what allows linear mode — a plain gain — instead of a dynamic
    compression that would crush the track's dynamics.
    """
    return (f"loudnorm=I={opts.lufs}:TP={opts.true_peak}:LRA={TARGET_LRA}"
            f":measured_I={stats['input_i']}:measured_TP={stats['input_tp']}"
            f":measured_LRA={stats['input_lra']}:measured_thresh={stats['input_thresh']}"
            f":offset={stats['target_offset']}:linear=true:print_format=summary")


def filter_chain(opts: RenderOptions, stats: dict[str, Any]) -> list[str]:
    chain = [loudnorm_filter(opts, stats)]
    if opts.head > 0:
        ms = int(opts.head * 1000)
        chain.append(f"adelay={ms}|{ms}")
    if opts.tail > 0:
        chain.append(f"apad=pad_dur={opts.tail}")
    # Mandatory: loudnorm outputs at 192 kHz unless the rate is imposed again.
    chain.append(f"aresample={opts.sample_rate}")
    return chain


def codec_args(opts: RenderOptions) -> list[str]:
    if opts.flac:
        return ["-c:a", "flac", "-sample_fmt", "s32" if opts.bits == 24 else "s16"]
    return ["-c:a", "pcm_s24le" if opts.bits == 24 else "pcm_s16le"]


def normalise(src: Path, out: Path, opts: RenderOptions,
              stats: dict[str, Any]) -> str | None:
    """Write the master. Returns None if all went well, the error message otherwise."""
    res = subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(src),
         "-af", ",".join(filter_chain(opts, stats)),
         "-ar", str(opts.sample_rate), *codec_args(opts), str(out)],
        capture_output=True, text=True)
    return None if res.returncode == 0 else res.stderr.strip()
