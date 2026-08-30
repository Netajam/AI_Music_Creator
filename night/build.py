#!/usr/bin/env python3
"""Turns a collection module into lyrics files, presets and queued jobs.

A collection lives in night/collections/<name>.py and defines COLLECTION (the
metadata) and SONGS (a list of dicts). This script writes the three artefacts
each song needs and, on the way, enforces the rules the recipe book paid for:

  * a style description under 512 characters (--style is rejected past that,
    and only after the preset has loaded);
  * only the eight tags the model actually reads as sections;
  * a lyric density in the band that has worked, reported per song;
  * a chorus repeated word for word.

A violation is a hard failure here rather than a wasted seven-minute take.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# `aimc.workspace` is the one place that knows whether the content lives in
# this repo or in the private one cloned inside it. See its `_workspace`.
from aimc.workspace import LYRICS, NIGHT, PRESETS  # noqa: E402

LEGAL_TAGS = {"Intro", "Verse", "Chorus", "Build", "Drop",
              "Breakdown", "Bridge", "Outro"}
TAG_RE = re.compile(r"^\[([A-Za-z]+)(?:\s*\d+)?\]\s*$")


def load(name: str):
    path = NIGHT / "collections" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"coll_{name}", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def syllables(text: str) -> float:
    """Roughly how many syllables a lyric holds, whatever script it is written in.

    Characters per second is a Latin-script measure: a line of Japanese carries
    far more singing in the same number of characters than a line of French, and
    banding both on `len(text)` rejected perfectly ordinary lyrics. Counting
    syllables instead makes one band work across every script the model accepts.
    Each rule is an approximation, and it only ever has to be good enough to
    separate "sparse" from "a recitation".
    """
    n = 0.0
    latin: list[str] = []
    for ch in text:
        o = ord(ch)
        if 0x3040 <= o <= 0x30FF:                      # kana: one mora each,
            n += 0.0 if ch in "ゃゅょャュョぁぃぅぇぉっッ" else 1.0   # small kana ride the previous one
        elif 0x4E00 <= o <= 0x9FFF:                    # han: ~2 morae in Japanese, 1 elsewhere
            n += 1.6
        elif 0xAC00 <= o <= 0xD7AF:                    # hangul: one block, one syllable
            n += 1.0
        elif 0x0600 <= o <= 0x06FF or 0x0900 <= o <= 0x097F:                    # arabic / urdu abjad
            n += 0.62
        elif 0x0E00 <= o <= 0x0E7F:                    # thai
            n += 0.5
        elif 0x0590 <= o <= 0x05FF:                    # hebrew
            n += 0.55
        else:
            latin.append(ch)
    # Latin, Cyrillic and Greek: a syllable is a run of vowels.
    # Latin, Greek and Cyrillic: a syllable is a run of vowels. Greek and
    # Cyrillic vowels have to be listed explicitly — leaving them out scored a
    # whole Greek lyric at 0.00 syllables per second.
    vowels = ("aeiouy"
              "àâäáãåæéèêëíìîïóòôöõøœúùûüÿıœ"
              "αεηιουωάέήίόύώϊϋΐΰ"
              "аеёиоуыэюяіїє")
    n += len(re.findall(f"[{vowels}]+", "".join(latin).lower()))
    return n


def check_lyrics(slug: str, text: str, duration: int,
                 sparse: bool = False) -> list[str]:
    """Section tags, density and chorus identity. Returns the problems found."""
    problems: list[str] = []
    tags, choruses, current = [], [], None
    buf: list[str] = []
    for line in text.splitlines():
        m = TAG_RE.match(line.strip())
        if m:
            if current == "Chorus":
                choruses.append("\n".join(buf).strip())
            tag = m.group(1)
            tags.append(tag)
            if tag not in LEGAL_TAGS:
                problems.append(f"illegal tag [{tag}] — the model reads it as a section")
            current, buf = tag, []
        else:
            if line.strip().startswith("[") and line.strip().endswith("]"):
                problems.append(f"invented cue {line.strip()} — read as a section, not a stage direction")
            buf.append(line)
    if current == "Chorus":
        choruses.append("\n".join(buf).strip())

    # Eight sections is what a verse/chorus song wants, and treating it as the
    # only legal shape is what made the first hundred sound like one songwriter.
    # A mantra, a one-riff track and a through-composed piece are all shorter.
    if not 3 <= len(tags) <= 12:
        problems.append(f"{len(tags)} sections — outside the 3 to 12 that have worked")
    if len(set(choruses)) > 1:
        problems.append("the chorus is not identical word for word between passes")

    body = "\n".join(l for l in text.splitlines() if not TAG_RE.match(l.strip()))
    dens = syllables(body) / duration
    # The omad take that was liked sits at 2.7 syllables/second; a fast deejay
    # flow reaches about 4. Below 0.8 the model tends to invent a structure of
    # its own — which is a real risk, and exactly what footwork, kwaito and
    # early dubstep sound like on purpose. A song may opt out with sparse=True,
    # and then carries the risk knowingly rather than being padded out of shape.
    floor = 0.45 if sparse else 0.8
    if not floor <= dens <= 5.0:
        problems.append(f"density {dens:.2f} syllables/s is outside the band that has worked")
    return problems


def main(names: list[str]) -> int:
    queue = NIGHT / "queue"
    queue.mkdir(parents=True, exist_ok=True)
    failures = 0
    for name in names:
        mod = load(name)
        coll = mod.COLLECTION
        order = coll.get("order", 0)
        lyr_dir = LYRICS / "night" / name
        pre_dir = PRESETS / "night" / name
        lyr_dir.mkdir(parents=True, exist_ok=True)
        pre_dir.mkdir(parents=True, exist_ok=True)
        print(f"\n── {coll['title']}  ({name}) ─────────────────")
        for i, song in enumerate(mod.SONGS, start=1):
            slug = song["slug"]
            duration = song["duration"]
            problems: list[str] = []
            if len(song["style"]) >= 512:
                problems.append(f"style is {len(song['style'])} characters, the limit is 512")

            instrumental = song.get("instrumental", False)
            preset = {
                "style": song["style"],
                "negative": song["negative"],
                "style_strength": song.get("style_strength", 0.4),
                "language": song.get("language", "fr"),
                "bpm": song["bpm"],
                "key": song["key"],
                "time_signature": song.get("time_signature", "4"),
                "duration": duration,
                "lm_temperature": song.get("lm_temperature", 0.85),
                "lm_cfg": song.get("lm_cfg", 2.2),
                "fade_out": song.get("fade_out", 4),
            }
            if song.get("fade_in"):
                preset["fade_in"] = song["fade_in"]
            if instrumental:
                preset["instrumental"] = True
            else:
                lyrics = song["lyrics"].strip() + "\n"
                problems += check_lyrics(slug, lyrics, duration, song.get("sparse", False))
                (lyr_dir / f"{slug}.txt").write_text(lyrics, encoding="utf-8")
                preset["lyrics"] = f"../../../lyrics/night/{name}/{slug}.txt"
            if song.get("reference"):
                preset["reference"] = f"../../../refs/{song['reference']}"
            else:
                preset.pop("style_strength", None)

            (pre_dir / f"{slug}.json").write_text(
                json.dumps(preset, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            job = {
                "slug": slug,
                "title": song["title"],
                "voice": song.get("voice", ""),
                "era": song.get("era", ""),
                "form": song.get("form", ""),
                "collection": name,
                "preset": f"presets/night/{name}/{slug}.json",
                "seed": song.get("seed", 1),
                "steps": song.get("steps", 8),
                "extra": song.get("extra", ""),
            }
            job_name = f"{order:02d}{i:02d}-{name}-{slug}.json"
            # A collection is rebuilt every time it grows, so a song already
            # rendered (or already tried and failed) must not be queued twice.
            already = any((NIGHT / d / job_name).exists()
                          for d in ("done", "failed"))
            if not already:
                (queue / job_name).write_text(
                    json.dumps(job, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            body = "" if instrumental else "\n".join(
                l for l in song["lyrics"].splitlines() if not TAG_RE.match(l.strip()))
            mark = "✗" if problems else ("·" if already else "✓")
            extra = "instrumental" if instrumental else f"{syllables(body)/duration:4.2f} syl/s"
            print(f"  {mark} {slug:<26} {song['bpm']:>3}bpm {song.get('language','fr'):>3} "
                  f"{extra:>13}  {song.get('voice','')[:34]}")
            for p in problems:
                print(f"      ! {p}")
                failures += 1
    print(f"\n{'✗ ' + str(failures) + ' problems' if failures else '✓ all clean'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
