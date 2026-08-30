"""./grab — fetches a track's audio from YouTube / YouTube Music.

Used to feed the pipeline with style references: you download a track, then
`blend-refs` takes from it the excerpts that will serve as conditioning.

    ./grab "https://music.youtube.com/watch?v=..."
    ./grab "daft punk around the world"        # search, takes the first result
    ./grab "stromae alors on danse" --list     # shows the results without downloading

Then:

    ./blend-refs refs/downloads/the-track.mp3=45 -o refs/melange.wav
    ./song --preset presets/electro-house.json --reference refs/melange.wav

Downloading from YouTube goes against its terms of service, and the tracks
fetched remain under copyright unless they are yours, in the public domain or
under a free licence. Personal use.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from aimc.audio import duration, install_hint, missing
from aimc.workspace import REFS

DEFAULT_OUT = REFS / "downloads"
SEARCH_RESULTS = 5
REQUIRED_TOOLS = ("yt-dlp", "ffmpeg")


def is_url(text: str) -> bool:
    return text.startswith(("http://", "https://", "www."))


def build_query(target: str) -> str:
    """A URL goes through as-is; otherwise we query YouTube's search."""
    return target if is_url(target) else f"ytsearch{SEARCH_RESULTS}:{target}"


def list_results(target: str) -> int:
    """Show the results of a search without downloading anything."""
    if is_url(target):
        print("That is already a URL — nothing to search for.", file=sys.stderr)
        return 1

    proc = subprocess.run(
        ["yt-dlp", "--flat-playlist", "--dump-json", "--no-warnings",
         build_query(target)],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        print(f"Search failed:\n{proc.stderr.strip()}", file=sys.stderr)
        return 1

    found = False
    print(f'Results for "{target}":\n')
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        found = True
        dur = item.get("duration")
        mins = f"{int(dur)//60}:{int(dur)%60:02d}" if dur else "  ?  "
        print(f"  {mins}  {item.get('title', '(untitled)')}")
        print(f"         {item.get('url') or item.get('id')}")
    if not found:
        print("  (no results)")
        return 1
    print("\nRun it again with the chosen URL to download.")
    return 0


def download_command(target: str, out_dir: Path, audio_format: str,
                     quality: str) -> list[str]:
    """The yt-dlp line, kept apart so it can be read at a glance.

    `--no-playlist`: a search returns a playlist, we only want the first item.
    `--restrict-filenames`: avoids spaces and accents, which complicate
    blend-refs' 'file=offset' arguments.
    """
    return [
        "yt-dlp",
        "--no-playlist", "--playlist-items", "1",
        "--no-overwrites",  # never rewrite a track that is already downloaded
        "--extract-audio",
        "--audio-format", audio_format,
        "--audio-quality", quality,
        "--restrict-filenames",
        "--no-warnings",
        "--embed-metadata",
        "--print", "after_move:filepath",
        "-o", str(out_dir / "%(title)s.%(ext)s"),
        build_query(target),
    ]


def report_failure(err: str) -> int:
    print(f"Download failed:\n{err}", file=sys.stderr)
    if "Sign in to confirm" in err or "bot" in err.lower():
        print("\nYouTube is asking for a check. Try it with your browser's "
              "cookies:\n"
              "  yt-dlp --cookies-from-browser safari ...", file=sys.stderr)
    return 1


def download(target: str, out_dir: Path, audio_format: str, quality: str) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(download_command(target, out_dir, audio_format, quality),
                          capture_output=True, text=True)
    if proc.returncode != 0:
        return report_failure(proc.stderr.strip() or proc.stdout.strip())

    paths = [Path(line.strip()) for line in proc.stdout.splitlines()
             if line.strip() and Path(line.strip()).exists()]
    if not paths:
        print("Download finished but the file cannot be found.", file=sys.stderr)
        return 1

    for path in paths:
        dur = duration(path)
        size = path.stat().st_size / 1e6
        print(f"\n{path}")
        print(f"  {dur:.0f} s, {size:.1f} MB" if dur else f"  {size:.1f} MB")
        print(f"\n  ./blend-refs {path}=45 -o refs/melange.wav")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="grab",
        description="Downloads a track's audio to serve as a style reference.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""examples:
  ./grab "https://music.youtube.com/watch?v=XXXX"
  ./grab "artist - title"                  # searches and takes the first result
  ./grab "artist - title" --list           # shows the results, downloads nothing
  ./grab URL --format wav                  # lossless, for a better reference

Then:
  ./blend-refs refs/downloads/title.mp3=45 -o refs/melange.wav
  ./song --preset presets/electro-house.json --reference refs/melange.wav
""",
    )
    parser.add_argument("target", metavar="URL_OR_SEARCH",
                        help="YouTube/YouTube Music URL, or search terms")
    parser.add_argument("--list", "-l", action="store_true",
                        help="show the search results without downloading")
    parser.add_argument("--format", "-f", default="mp3",
                        choices=["mp3", "wav", "flac", "m4a", "opus"],
                        help="audio format (default: mp3; wav/flac for a "
                             "lossless reference)")
    parser.add_argument("--quality", "-q", default="0", metavar="N",
                        help="yt-dlp VBR quality, 0 = best (default: 0)")
    parser.add_argument("--out", "-o", default=str(DEFAULT_OUT), metavar="FOLDER",
                        help=f"output folder (default: {DEFAULT_OUT})")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    absent = missing(*REQUIRED_TOOLS)
    if absent:
        parser.error(install_hint(absent))

    if args.list:
        return list_results(args.target)
    return download(args.target, Path(args.out).expanduser(),
                    args.format, args.quality)


if __name__ == "__main__":
    sys.exit(main())
