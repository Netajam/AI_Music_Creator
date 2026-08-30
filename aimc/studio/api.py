"""The studio's routes. Each one assembles, none of them computes.

Everything they serve comes from the neighbouring modules: the measurements from
`measures`, the list from `takes`, the locks from `jobs`, the commands from
`commands`. A route that decided something here would be a second definition of
what `./song` and `./master` already do.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

from aimc.audio import install_hint, missing
from aimc.generation.catalog import STYLE_MAX_CHARS, TRACK_NAMES
from aimc.mastering import (
    LUFS_TOLERANCE,
    TAIL_MAX,
    TARGET_LRA,
    TARGET_LUFS,
    TARGET_TP,
)
from aimc.provenance import manifest_for, short_fingerprint
from aimc.references import picks as picks_store
from aimc.references.grab import REQUIRED_TOOLS as GRAB_TOOLS
from aimc.studio import inspiration
from aimc.studio.commands import (
    GrabRequest,
    MasterRequest,
    ReferenceRequest,
    RunRequest,
    build_blend_command,
    build_command,
    build_grab_command,
    build_master_command,
)
from aimc.studio.jobs import (
    align_job,
    foreign_generation,
    grab_job,
    job,
    master_job,
    stem_job,
)
from aimc.studio.library import (
    alignment,
    code_status,
    energy_profile,
    fingerprint,
    in_dir,
    loudness,
    manifest_kind,
    read_dir,
    read_manifest,
    readiness,
    song_file,
    stems,
    structure,
    takes,
)
from aimc.studio.library.cache import store
from aimc.studio.library.paths import download_file, media_file
from aimc.studio.reconstruct import ReconstructRequest, deduce, reconstructed_manifest
from aimc.workspace import CACHE, LYRICS, PRESETS, REFS

INDEX = Path(__file__).resolve().parent / "studio.html"

# Default values for the master form's fields, served rather than copied into
# studio.html.
MASTER_DEFAULTS = {"head": 1.0, "tail": 2.0, "bits": 24}

app = FastAPI(title="AI Music Studio")


@app.get("/api/state")
def state() -> dict[str, Any]:
    return {
        "foreign_pid": foreign_generation(),
        "takes": takes(),
        "presets": read_dir(PRESETS, ".json"),
        "lyrics": read_dir(LYRICS, ".txt"),
        "refs": [p.name for p in REFS.glob("*.wav")] if REFS.is_dir() else [],
        "tracks": TRACK_NAMES,
        "inspirations": inspiration.listing(),
        "job": job.state(),
        "master": master_job.state(),
        "align": align_job.state(),
        "stems": stem_job.state(),
        "grab": grab_job.state(),
        # Served rather than copied into studio.html: a single definition of
        # "on target", mastering's.
        "targets": {"lufs": TARGET_LUFS, "true_peak": TARGET_TP, "lra": TARGET_LRA,
                    "tail_max": TAIL_MAX, "lufs_tolerance": LUFS_TOLERANCE,
                    **MASTER_DEFAULTS},
        # Same reason: the style box counts against the limit `./song` enforces,
        # and a second copy of the number would let the two disagree.
        "limits": {"style_chars": STYLE_MAX_CHARS},
    }


@app.get("/api/take/{name}")
def take(name: str) -> dict[str, Any]:
    f = song_file(name)
    data = read_manifest(f)
    fp = fingerprint(f)
    return {
        "name": f.name,
        "energy": energy_profile(f),
        "loudness": loudness(f),
        "structure": structure(f),
        "manifest": data,
        "manifest_kind": manifest_kind(data),
        "fingerprint": fp,
        "fingerprint_short": short_fingerprint(fp),
        "ready": readiness(f),
        "code": code_status(data),
        # Never computed here: served if it already exists and does speak of the
        # text this manifest carries today.
        "alignment": alignment(f, (data or {}).get("lyrics")),
        # Never computed here either, and for a blunter reason: a separation
        # costs a third of the track's duration and 2.3 GB. It is asked for.
        "stems": stems(f),
    }


@app.get("/api/probe/{name}")
def probe_take(name: str) -> dict[str, Any]:
    """Fingerprint + readiness of a take, computed on demand.

    Deliberately separate from /api/state: these two measurements cost a full
    decode per file, and the list of takes has to appear without waiting for
    them.
    """
    f = song_file(name)
    fp = fingerprint(f)
    verdict = readiness(f)
    return {"name": f.name, "fingerprint": fp,
            "fingerprint_short": short_fingerprint(fp),
            "ready": verdict.get("ready"), "missing": verdict.get("missing"),
            "unknown": verdict.get("unknown"), "measured": verdict.get("measured"),
            "codec": verdict.get("codec")}


@app.get("/audio/{name}")
def audio(name: str) -> FileResponse:
    return FileResponse(song_file(name))


@app.get("/api/preset/{name}")
def preset(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(
        in_dir(PRESETS, name, "preset not found").read_text(encoding="utf-8"))
    return data


@app.get("/api/lyrics/{name}")
def lyrics_file(name: str) -> dict[str, Any]:
    f = in_dir(LYRICS, name, "lyrics not found")
    return {"name": f.name, "text": f.read_text(encoding="utf-8")}


@app.post("/api/preview")
def preview(r: RunRequest) -> dict[str, Any]:
    """The exact command, without launching anything — to see what is being sent."""
    return {"command": " ".join(build_command(r))}


@app.post("/api/run")
def run(r: RunRequest) -> dict[str, Any]:
    stray = foreign_generation()
    if stray is not None:
        raise HTTPException(
            409, f"A generation is already running outside the studio (pid "
                 f"{stray}). Wait for it to finish: two generations at once "
                 f"exhaust the 16 GB and both fail.")
    cmd = build_command(r)
    job.start(cmd)
    return {"command": " ".join(cmd)}


@app.get("/api/job")
def job_state() -> dict[str, Any]:
    st = job.state()
    st["foreign_pid"] = foreign_generation()
    return st


@app.post("/api/job/stop")
def job_stop() -> dict[str, Any]:
    return {"stopped": job.stop()}


@app.post("/api/master")
def master(r: MasterRequest) -> dict[str, Any]:
    """Master from the browser. The refusal of a compressed source stays
    `./master`'s: we do not replay it here, we let it speak."""
    cmd = build_master_command(r)
    master_job.start(cmd)
    return {"command": " ".join(cmd)}


@app.get("/api/master/state")
def master_state() -> dict[str, Any]:
    return master_job.state()


@app.post("/api/master/stop")
def master_stop() -> dict[str, Any]:
    return {"stopped": master_job.stop()}


@app.post("/api/align/{name}")
def align(name: str) -> dict[str, Any]:
    """Place the manifest's lyrics in the timeline of the track.

    The text comes from the manifest and from nowhere else: `lyrics/<name>.txt`
    may have been rewritten since generation, and aligning against it would
    produce a wrong and credible result.
    """
    f = song_file(name)
    data = read_manifest(f)
    if data is None:
        raise HTTPException(
            409, "This take predates settings tracking: the lyrics it was "
                 "given were not recorded, so there is nothing to align.")
    if (data.get("params") or {}).get("instrumental") is True:
        raise HTTPException(409, "Instrumental take: there are no lyrics to place.")
    text = data.get("lyrics") or ""
    if not text.strip():
        raise HTTPException(409, "The settings record no lyrics for this take.")

    stray = foreign_generation()
    if stray is not None:
        raise HTTPException(
            409, f"A generation is running (pid {stray}). Aligning loads a "
                 f"second model: wait for it to finish, or the 16 GB run out.")
    if job.running:
        raise HTTPException(409, "A generation is running. Wait for it to finish.")

    CACHE.mkdir(exist_ok=True)
    # The text goes through a file: `./analyse --align` is handed the lyrics, it
    # does not go looking for them — here is where we know which ones are
    # authoritative.
    lyrics_file = CACHE / f"align-{f.stem}.txt"
    lyrics_file.write_text(text, encoding="utf-8")
    out = CACHE / f"align-{f.stem}.json"
    out.unlink(missing_ok=True)
    cmd = [sys.executable, "-m", "aimc.analysis.cli", str(f),
           "--align", str(lyrics_file), "--out", str(out)]
    align_job.start_for(f.name, out, cmd, [lyrics_file])
    return {"command": " ".join(cmd)}


@app.get("/api/align/state")
def align_state() -> dict[str, Any]:
    """Where the alignment has got to — and, if it has just finished, its filed result.

    This is where the result enters the cache: the subprocess writes it into a
    hand-off file and exits, knowing nothing about the studio's cache.
    """
    st = align_job.state()
    st["stored"] = False
    if not align_job.running and align_job.out is not None and align_job.out.exists():
        try:
            data = json.loads(align_job.out.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = None
        if isinstance(data, dict) and data.get("lines"):
            store(song_file(align_job.take or ""), "alignment", data)
            st["stored"] = True
        align_job.cleanup()
    return st


@app.post("/api/align/stop")
def align_stop() -> dict[str, Any]:
    return {"stopped": align_job.stop()}


@app.post("/api/stems/{name}")
def separate(name: str, source: str = "take", tags: bool = False) -> dict[str, Any]:
    """Pull a track apart into drums, bass, vocals and other.

    A take or an inspiration: `source` says which folder the name lives in, and
    the separation itself does not care — Demucs is handed a path. Asking it of
    a track we did not make is in fact the sharper question, since that is the
    one whose instrumentation nobody wrote down.

    With `tags`, the same pass also names the instrument families playing in
    `other` and the genre the mix sounds like. Asked for separately rather than
    always done, because it is not a rounding error: measured on a 40 s clip,
    the pass goes from 8 s to 15 s — the tagger runs a forward pass per chunk
    on top of Demucs', and nearly doubles a wait that is already the reason
    nothing here starts on its own.

    Refused under the same conditions as an alignment, and for the same reason:
    a second set of weights alongside a generation is what exhausts the 16 GB.
    The `ModelJob` lock takes care of the other half — an alignment and a
    separation cannot run at once either.
    """
    f = media_file(source, name)
    stray = foreign_generation()
    if stray is not None:
        raise HTTPException(
            409, f"A generation is running (pid {stray}). Separating loads a "
                 f"second model: wait for it to finish, or the 16 GB run out.")
    if job.running:
        raise HTTPException(409, "A generation is running. Wait for it to finish.")

    CACHE.mkdir(exist_ok=True)
    # Named after the file in full, extension included: a take `X.wav` and an
    # inspiration `X.mp3` are two different tracks, and the hand-off file must
    # not be a place where they meet.
    out = CACHE / f"stems-{f.name.replace('.', '_')}.json"
    out.unlink(missing_ok=True)
    cmd = [sys.executable, "-m", "aimc.analysis.cli", str(f),
           "--stems", "--out", str(out)]
    if tags:
        cmd.append("--tags")
    stem_job.start_for(f.name, out, cmd, source=source)
    return {"command": " ".join(cmd)}


@app.get("/api/stems/state")
def stems_state() -> dict[str, Any]:
    """Where the separation has got to — and, if it has just finished, its result.

    Like the alignment's: the subprocess knows nothing about the cache, so the
    hand-off file is filed away here.
    """
    st = stem_job.state()
    st["stored"] = False
    if not stem_job.running and stem_job.out is not None and stem_job.out.exists():
        try:
            data = json.loads(stem_job.out.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = None
        if isinstance(data, dict) and data.get("presence"):
            store(media_file(stem_job.source, stem_job.take or ""), "stems", data)
            st["stored"] = True
        stem_job.cleanup()
    return st


@app.post("/api/stems/stop")
def stems_stop() -> dict[str, Any]:
    return {"stopped": stem_job.stop()}


# ------------------------------------------------------------- inspirations
# Tracks we did not make, read with the same analysis as a take and served by a
# route of their own — a foreign track has no manifest, no seed and no verdict
# on publishing, and half of /api/take would have come back null (see
# `studio/inspiration.py`).


class PickRequest(BaseModel):
    """A moment kept in an inspiration, and what the listener heard in it.

    `until` turns the moment into a passage: the measurements are then read over
    the whole span rather than sampled at one second. It never changes what a
    reference cuts — ten seconds from `at`, which is all the engine reads.
    """

    at: int
    until: int | None = None
    note: str = ""


def analysed_seconds(f: Path) -> int:
    """How many seconds of this track the studio can point at.

    The energy profile's axis — one value per second — and not the duration the
    container reports, which overshoots by up to a second. The browser draws on
    that same axis, so a second it can point at is a second these routes can
    read.
    """
    return len(energy_profile(f).get("low") or [])


def checked_moment(f: Path, at: int) -> int:
    seconds = analysed_seconds(f)
    if not 0 <= at < max(seconds, 1):
        raise HTTPException(
            400, f"{at} s is outside the track ({seconds} s analysed).")
    return at


def checked_span(f: Path, start: int, end: int) -> tuple[int, int]:
    """A passage clipped to what was actually analysed.

    The end is clamped rather than refused: the last section's bound is the end
    of the analysis itself, and the two decoders behind it (16 kHz for the
    energy, 22 kHz for the structure) can disagree by the final second. Refusing
    would make the last row of the table the one section that cannot be read.
    """
    start = checked_moment(f, start)
    if end <= start:
        raise HTTPException(
            400, f"A passage has to end after it starts: {start} s to {end} s.")
    return start, min(end, analysed_seconds(f))


@app.post("/api/grab")
def grab(r: GrabRequest) -> dict[str, Any]:
    """Download a track to take inspiration from. Calls `./grab`, decides nothing.

    Downloading from YouTube goes against its terms of service, and what comes
    back stays under copyright unless it is yours, in the public domain or under
    a free licence — grab's own docstring says so, and the form says it too, at
    the place where the URL is pasted.
    """
    if not r.url.strip():
        raise HTTPException(400, "Paste a URL, or something to search for.")
    absent = missing(*GRAB_TOOLS)
    if absent:
        raise HTTPException(409, install_hint(absent))
    cmd = build_grab_command(r)
    grab_job.start_for(r.url.strip(), cmd)
    return {"command": " ".join(cmd)}


@app.get("/api/grab/state")
def grab_state() -> dict[str, Any]:
    """Where the download has got to — and, once it lands, where the track came from.

    This is the only moment at which the URL and the file are both known: the
    file is named after the video's title, and `./grab` keeps no note of what
    was asked for. Recorded here, in the pick file, which is the half of the
    pair that is versioned and survives deleting the audio.

    `arrived` empty with a clean exit is not a failure: `--no-overwrites` means
    a URL asked for twice writes nothing at all. The browser says "you already
    have this one" rather than showing an error that is not one.
    """
    st = grab_job.state()
    if not grab_job.running and not grab_job.settled:
        for name in grab_job.settle():
            picks_store.remember_source(name, grab_job.url)
        st["arrived"] = list(grab_job.arrived)
    return st


@app.post("/api/grab/stop")
def grab_stop() -> dict[str, Any]:
    return {"stopped": grab_job.stop()}


@app.get("/api/inspiration/{name}")
def inspiration_detail(name: str) -> dict[str, Any]:
    return inspiration.detail(name)


@app.get("/inspiration-audio/{name}")
def inspiration_audio(name: str) -> FileResponse:
    return FileResponse(download_file(name))


@app.get("/api/inspiration/{name}/measure")
def measure_span(name: str, start: int, end: int) -> dict[str, Any]:
    """What a passage of an inspiration is like, read over its whole length.

    A pure read, and a cheap one: `structure` and `energy_profile` were computed
    when the track was opened and are cached from then on, so this only
    aggregates numbers that already exist. Which is why clicking a section can
    answer straight away, with no job, no lock and no poll.
    """
    f = download_file(name)
    start, end = checked_span(f, start, end)
    return inspiration.measured_over(f.name, start, end)


@app.post("/api/inspiration/{name}/picks")
def add_pick(name: str, r: PickRequest) -> dict[str, Any]:
    """Keep a moment or a passage, with everything measurable frozen alongside.

    The measurements are taken now and stored, not looked up later: the analysis
    is redone whenever the audio changes, and a pick that pointed at it would
    quietly start describing a different second.
    """
    f = download_file(name)
    if r.until is None:
        at = checked_moment(f, r.at)
        return picks_store.add(f.name, at, r.note, inspiration.measured_at(f.name, at))
    start, end = checked_span(f, r.at, r.until)
    return picks_store.add(f.name, start, r.note,
                           inspiration.measured_over(f.name, start, end), until=end)


@app.put("/api/inspiration/{name}/picks/{pick_id}")
def edit_pick(name: str, pick_id: str, r: PickRequest) -> dict[str, Any]:
    """Rewrite the words of a pick. Its span and its measurements do not move."""
    f = download_file(name)
    pick = picks_store.update(f.name, pick_id, r.note)
    if pick is None:
        raise HTTPException(404, "No such pick.")
    return pick


@app.delete("/api/inspiration/{name}/picks/{pick_id}")
def drop_pick(name: str, pick_id: str) -> dict[str, Any]:
    f = download_file(name)
    return {"removed": picks_store.remove(f.name, pick_id)}


@app.post("/api/inspiration/{name}/reference")
def build_reference(name: str, r: ReferenceRequest) -> dict[str, Any]:
    """Stitch the chosen moments into a 30 s style reference, via `./blend-refs`.

    Run in the foreground, unlike everything else the studio launches: this is
    three ffmpeg extractions of 10 s and a concat, about a second in all. A job,
    a lock and a poll would be more machinery than the wait it is hiding.

    One track at a time, and that is the recipe book's rule rather than a
    limitation of the form: a blend holding two tempos makes a take that speeds
    up and slows down for no reason. Moments taken from one track cannot
    disagree about the tempo.
    """
    f = download_file(name)
    if not r.ats:
        raise HTTPException(400, "Choose at least one moment.")
    if len(r.ats) > picks_store.MAX_PER_REFERENCE:
        raise HTTPException(
            400, f"{len(r.ats)} moments chosen, but a reference has "
                 f"{picks_store.MAX_PER_REFERENCE} slots of 10 s. Keep "
                 f"{picks_store.MAX_PER_REFERENCE} at most.")

    out = inspiration.reference_path(f.name)
    cmd = build_blend_command(f, r.ats, out)
    done = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if done.returncode != 0 or not out.exists():
        raise HTTPException(
            502, (done.stderr or done.stdout).strip() or "blend-refs failed.")
    return {"reference": out.name, "command": " ".join(cmd),
            "log": done.stdout.strip()}


@app.get("/api/reconstruct/{name}")
def reconstruct_prefill(name: str) -> dict[str, Any]:
    f = song_file(name)
    existing = read_manifest(f)
    return {
        "name": f.name,
        "has_manifest": existing is not None,
        "manifest_kind": manifest_kind(existing),
        "deduced": deduce(f),
    }


@app.post("/api/reconstruct/{name}")
def reconstruct(name: str, r: ReconstructRequest) -> dict[str, Any]:
    """Attach a manifest to an orphaned take, without ever passing it off as an
    original manifest."""
    f = song_file(name)
    existing = manifest_for(f)
    if existing is not None and not r.confirm:
        raise HTTPException(
            409, f"{existing.name} already exists for this take. Confirm to "
                 f"replace it — original settings are worth more than "
                 f"reconstructed ones.")

    manifest = reconstructed_manifest(f, r, deduce(f))
    # Always `<full filename>.json`, never `<stem>.json`: a reconstruction must
    # on no account end up attached to a namesake that contains another take —
    # that is exactly the pouf-seed1.mp3 / pouf-seed1.wav case.
    target = f.with_name(f.name + ".json")
    target.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"written": target.name, "manifest": manifest}


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return INDEX.read_text(encoding="utf-8")
