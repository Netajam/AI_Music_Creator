"""The command lines the studio launches — and nothing more.

The studio has no generation or mastering logic of its own: it only has buttons.
The requests below are flat because they trace the options of `./song` and
`./master`; that is what makes the translation below verifiable at a glance, and
the refusal of a compressed source stays `./master`'s, which we let speak.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel

from aimc.studio.jobs import MASTER_REPORT
from aimc.studio.library import song_file
from aimc.workspace import LYRICS, PRESETS, REFS, REPO_ROOT, SONGS

SONG_CLI = REPO_ROOT / "song"
MASTER_CLI = REPO_ROOT / "master"
GRAB_CLI = REPO_ROOT / "grab"
BLEND_CLI = REPO_ROOT / "blend-refs"


class RunRequest(BaseModel):
    preset: str | None = None
    # The style prompt, when the form overrides the preset's. Sent as `--style`,
    # which on the command line *replaces* the preset's value rather than
    # extending it (see command/presets.py) — so the form fills this box with
    # the preset's own text before adding to it, and an empty box means "the
    # preset's, untouched".
    style: str | None = None
    lyrics: str | None = None
    reference: str | None = None
    style_strength: float | None = None
    bpm: int | None = None
    duration: float | None = None
    seed: int | None = None
    steps: int | None = None
    fmt: str = "wav"
    lm_temperature: float | None = None
    negative: str | None = None
    infer_method: str | None = None
    # adding a track (lego): the source is a take from songs/
    lego: str | None = None
    lego_track: str | None = None
    lego_from: float | None = None
    lego_to: float | None = None
    # touch-up
    repaint: str | None = None
    repaint_from: float | None = None
    repaint_to: float | None = None
    repaint_mode: str | None = None
    retake_seed: int | None = None
    retake_variance: float | None = None
    dry_run: bool = False


class GrabRequest(BaseModel):
    url: str
    # Lossless where `./grab` itself defaults to mp3: a reference is fed to the
    # engine, not listened to, and grab's own help recommends wav for one. The
    # form can still choose otherwise.
    fmt: str = "wav"


class ReferenceRequest(BaseModel):
    """The moments of one inspiration to stitch into a 30 s style reference."""

    ats: list[float]


class MasterRequest(BaseModel):
    name: str
    lufs: float | None = None
    true_peak: float | None = None
    head: float | None = None
    tail: float | None = None
    bits: int | None = None
    flac: bool = False
    force: bool = False


def _flags(pairs: list[tuple[str, Any]]) -> list[str]:
    """An option and its value, for each value that is set."""
    out: list[str] = []
    for flag, value in pairs:
        if value is not None:
            out += [flag, str(value)]
    return out


def build_command(r: RunRequest) -> list[str]:
    """The `./song` command corresponding to this request."""
    # The file names arrive bare from the browser: they are read back inside the
    # folder they belong to, not taken for paths.
    cmd = [str(SONG_CLI), *_flags([
        ("--preset", PRESETS / r.preset if r.preset else None),
        ("--style", r.style),
        ("--lyrics", LYRICS / r.lyrics if r.lyrics else None),
        ("--reference", REFS / r.reference if r.reference else None),
        ("--style-strength", r.style_strength),
        ("--bpm", r.bpm), ("--duration", r.duration), ("--seed", r.seed),
        ("--steps", r.steps), ("--format", r.fmt),
        ("--lm-temperature", r.lm_temperature), ("--negative", r.negative),
        ("--infer-method", r.infer_method),
        ("--lego", SONGS / r.lego if r.lego else None),
        ("--lego-track", r.lego_track),
        ("--lego-from", r.lego_from), ("--lego-to", r.lego_to),
        ("--repaint", SONGS / r.repaint if r.repaint else None),
        ("--repaint-from", r.repaint_from), ("--repaint-to", r.repaint_to),
        ("--repaint-mode", r.repaint_mode),
        ("--retake-seed", r.retake_seed), ("--retake-variance", r.retake_variance),
    ])]
    if r.dry_run:
        cmd.append("--dry-run")
    return cmd


def build_master_command(r: MasterRequest) -> list[str]:
    """The `./master` command corresponding to this request."""
    cmd = [str(MASTER_CLI), str(song_file(r.name)), *_flags([
        ("--lufs", r.lufs), ("--true-peak", r.true_peak),
        ("--head", r.head), ("--tail", r.tail), ("--bits", r.bits),
    ])]
    if r.flac:
        cmd.append("--flac")
    if r.force:
        cmd.append("--force")
    cmd += ["--report", str(MASTER_REPORT)]
    return cmd


def build_grab_command(r: GrabRequest) -> list[str]:
    """The `./grab` command corresponding to this request.

    `--` before the target, and this is not decoration: what is pasted into the
    field is arbitrary text, and a line starting with a dash would otherwise be
    read as an option — `--out` is one of grab's own. There is no shell here, so
    nothing worse could happen than the wrong flag being honoured; that is
    already enough.
    """
    return [str(GRAB_CLI), "--format", r.fmt, "--", r.url]


def build_blend_command(source: Path, ats: list[float], out: Path) -> list[str]:
    """The `./blend-refs` command that turns kept moments into a style reference.

    One track, several offsets: the recipe book's rule is one reference, one
    tempo grid, and moments taken from the same track cannot disagree about the
    tempo. The 10 s slot and the three-slot limit are blend's, not repeated here.
    """
    specs = [f"{source}={at:g}" for at in ats]
    return [str(BLEND_CLI), "-o", str(out), "--", *specs]
