#!/usr/bin/env python3
"""Reads back what the night actually produced, take by take.

This does NOT say whether a song is good — `./analyse` counts sections and
measures bass energy and has no idea whether any of it sounds right, and the
recipe book is emphatic that it must be used to confirm an impression rather
than to form one. What it does catch is the failures that are visible without
ears, and every one of them is a failure this project has already paid for:

  * a take that came back at a tempo the preset did not ask for;
  * a take that heard three sections where eight were written — the "flat,
    nothing ever lifts" shape;
  * a take that heard fifteen — the "all over the place" shape;
  * a take with no drop at all, or with no vocal where a lyric was supplied;
  * a bass energy that never moves, which is a song with no dynamics.

Run it after the queue has drained, not during: it costs CPU the renderer wants.

    python3 night/verify.py            # every take in the ledger
    python3 night/verify.py neon-sud   # one collection
"""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# `aimc.workspace` is the one place that knows whether the content lives in
# this repo or in the private one cloned inside it. See its `_workspace`.
from aimc.workspace import NIGHT, PRESETS, WORKSPACE  # noqa: E402

REPORT = NIGHT / "verification.tsv"


def rows() -> list[dict[str, str]]:
    with (NIGHT / "ledger.tsv").open(encoding="utf-8") as fh:
        return [r for r in csv.DictReader(fh, delimiter="\t") if r["status"] == "ok"]


def analyse(path: Path) -> dict | None:
    try:
        out = subprocess.run(["./analyse", "--json", str(path)], cwd=ROOT,
                             capture_output=True, text=True, timeout=900)
    except subprocess.TimeoutExpired:
        return None
    if out.returncode != 0:
        return None
    try:
        return json.loads(out.stdout)
    except json.JSONDecodeError:
        return None


def judge(want_bpm: int, got: dict, has_lyrics: bool) -> tuple[str, list[str]]:
    """The flags are shapes this project has already been burned by, nothing more."""
    sections = got.get("sections") or []
    drops = got.get("drops") or []
    tempo = got.get("tempo_global") or 0
    basses = [s.get("bass", 0) for s in sections]
    vocal = any(s.get("has_vocal") for s in sections)

    notes = []
    # A half-time reading is the analyser being right about a jungle track, not
    # a fault: the all-dayggering card records exactly that.
    if tempo and not (abs(tempo - want_bpm) <= 4 or abs(tempo * 2 - want_bpm) <= 6
                      or abs(tempo / 2 - want_bpm) <= 4):
        notes.append(f"tempo {tempo:.0f} against {want_bpm} asked")
    if len(sections) <= 4:
        notes.append(f"only {len(sections)} sections heard — the flat shape")
    if len(sections) >= 15:
        notes.append(f"{len(sections)} sections heard — the scattered shape")
    if not drops:
        notes.append("no drop anywhere")
    if basses and max(basses) - min(basses) < 0.25:
        notes.append(f"bass barely moves ({min(basses):.2f}–{max(basses):.2f})")
    if has_lyrics and not vocal:
        notes.append("no vocal detected on a take that has lyrics")
    return ("flagged" if notes else "clean"), notes


def main(only: str | None) -> int:
    todo = [r for r in rows() if not only or r["collection"] == only]
    print(f"{len(todo)} take(s) to read back\n")
    out = REPORT.open("w", encoding="utf-8", newline="")
    w = csv.writer(out, delimiter="\t")
    w.writerow(["slug", "collection", "verdict", "tempo_asked", "tempo_heard",
                "sections", "drops", "bass_low", "bass_high", "vocal", "notes"])
    flagged = 0
    for r in todo:
        audio = WORKSPACE / r["audio"]
        preset = json.loads((PRESETS / "night" / r["collection"]
                             / f"{r['slug']}.json").read_text())
        got = analyse(audio)
        if got is None:
            print(f"  ? {r['slug']:<28} could not be analysed")
            w.writerow([r["slug"], r["collection"], "unreadable", preset["bpm"],
                        "", "", "", "", "", "", "analyse failed"])
            flagged += 1
            continue
        verdict, notes = judge(preset["bpm"], got, "lyrics" in preset)
        secs = got.get("sections") or []
        basses = [s.get("bass", 0) for s in secs] or [0]
        w.writerow([r["slug"], r["collection"], verdict, preset["bpm"],
                    round(got.get("tempo_global") or 0), len(secs), len(got.get("drops") or []),
                    f"{min(basses):.2f}", f"{max(basses):.2f}",
                    any(s.get("has_vocal") for s in secs), "; ".join(notes)])
        mark = "·" if verdict == "clean" else "!"
        print(f"  {mark} {r['slug']:<28} {len(secs):>2} sections, "
              f"{len(got.get('drops') or []):>1} drops, bass "
              f"{min(basses):.2f}–{max(basses):.2f}"
              + (f"  — {'; '.join(notes)}" if notes else ""))
        flagged += verdict != "clean"
    out.close()
    print(f"\n{len(todo) - flagged} clean, {flagged} flagged → {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else None))
