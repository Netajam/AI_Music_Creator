"""./analyse — structural analysis of a track, its lyrics, and its stems.

    ./analyse songs/the-track.wav          # readable in the terminal
    ./analyse songs/the-track.wav --json   # for the studio
    ./analyse songs/the-track.wav --align  # where each lyric line is
    ./analyse songs/the-track.wav --stems  # which families actually play
    ./analyse songs/the-track.wav --tags   # and what they are, by name

    ./analyse songs/the-track.wav --align --lyrics text.txt

Alignment is handed the text, it does not go looking for it: it is up to the
caller to know which one is authoritative. The studio takes the one from the
take's manifest — never `lyrics/`, which nothing stops from having been
rewritten since.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from aimc.analysis.render import render
from aimc.analysis.track import analyse


def main() -> int:
    ap = argparse.ArgumentParser(
        prog="analyse", description="Structural analysis of a track.")
    ap.add_argument("audio")
    ap.add_argument("--json", action="store_true", help="raw JSON output")
    ap.add_argument("--align", metavar="LYRICS",
                    help="place each line of this lyrics file in the timeline "
                         "of the track")
    ap.add_argument("--stems", action="store_true",
                    help="separate the mix into drums, bass, vocals and other, "
                         "and report which of them actually play")
    ap.add_argument("--tags", action="store_true",
                    help="name the instrument families playing inside `other`, "
                         "and the genre the mix sounds like. Implies --stems: "
                         "the families are read off the separated stem, so "
                         "there is nothing to tag without it")
    ap.add_argument("--out", help="write the JSON to this file rather than to "
                                  "standard output")
    args = ap.parse_args()

    path = Path(args.audio).expanduser()
    if not path.is_file():
        ap.error(f"file not found: {path}")

    if args.align:
        return align_lyrics(path, Path(args.align).expanduser(), args.out, ap)
    if args.stems or args.tags:
        return separate(path, args.out, args.tags)

    data = analyse(path)
    if args.json:
        print(json.dumps(data, ensure_ascii=False))
        return 0
    if "error" in data:
        print(data["error"], file=sys.stderr)
        return 1
    print(render(path, data))
    return 0


def align_lyrics(path: Path, lyrics: Path, out: str | None,
                 ap: argparse.ArgumentParser) -> int:
    """Place the lines of `lyrics` inside `path`, and return the result.

    Deliberately chatty: the caller is the studio, which displays this log for
    the minute it takes, and the very first run downloads a 1.2 GB model —
    without the log, nothing would say why nothing is happening.
    """
    from aimc.analysis.lyrics import align

    if not lyrics.is_file():
        ap.error(f"lyrics not found: {lyrics}")
    text = lyrics.read_text(encoding="utf-8")
    if not text.strip():
        print(f"{lyrics} is empty: nothing to place", file=sys.stderr)
        return 1

    print(f"aligning {path.name} against {lyrics.name} — the first run "
          f"downloads the MMS_FA model (~1.2 GB)", flush=True)
    result = align(path, text)
    if "error" in result:
        print(result["error"], file=sys.stderr)
        return 1

    payload = json.dumps(result, ensure_ascii=False)
    if out:
        Path(out).write_text(payload, encoding="utf-8")
        print(f"{len(result['lines'])} lines placed → {out}")
        return 0
    print(payload)
    return 0


def separate(path: Path, out: str | None, tag: bool = False) -> int:
    """Separate `path` into four stems and report what plays in each.

    Chatty for the same reason as the alignment: the studio shows this log for
    the minute it takes, and the first run downloads a 320 MB model.
    """
    from aimc.analysis.stems import analyse as analyse_stems

    weights = "the Demucs model (~320 MB)"
    if tag:
        weights = "the Demucs and AST models (~320 MB and ~350 MB)"
    print(f"separating {path.name} — the first run downloads {weights}",
          flush=True)
    result = analyse_stems(path, log=lambda line: print(line, flush=True), tag=tag)
    if "error" in result:
        print(result["error"], file=sys.stderr)
        return 1

    payload = json.dumps(result, ensure_ascii=False)
    if out:
        Path(out).write_text(payload, encoding="utf-8")
        playing = [s for s in result["sources"] if result["presence"][s]["present"]]
        print(f"{', '.join(playing) or 'nothing'} → {out}")
        if tag:
            print(_tag_line(result.get("tags") or {}))
        return 0
    print(payload)
    return 0


def _tag_line(tags: dict[str, Any]) -> str:
    """One line saying what was heard — and saying so when that is nothing.

    Silence is a result here and has to read like one: a track whose `other`
    holds only break bleed produces no family at all, and a blank line would
    look like the tagging had failed rather than answered.
    """
    heard = tags.get("heard") or []
    genres = tags.get("genres_heard") or []
    return (f"  playing in other: {', '.join(heard) or 'nothing above the bar'}"
            f" — sounds like: {', '.join(genres) or 'no genre above the bar'}")


if __name__ == "__main__":
    sys.exit(main())
