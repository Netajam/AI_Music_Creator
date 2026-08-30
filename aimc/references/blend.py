"""./blend-refs — builds a style reference out of SEVERAL tracks.

ACE-Step takes only one file in `--reference`, but it does not use the whole of
it: `process_reference_audio` takes three 10 s segments from it (start, middle,
end) and stitches them into a 30 s tensor.

When the file is exactly 30 s long, that slicing becomes deterministic —
`random.randint(0, max(0, 480000 - 480000))` is 0 for all three slots, so the
model reads exactly [0-10 s], [10-20 s], [20-30 s].

We can therefore fill those three slots with three different tracks: the model
receives them as three influences of equal weight.

    ./blend-refs a.mp3=45 b.mp3=30 c.mp3=12 -o refs/melange.wav
    ./song --preset presets/electro-house.json --reference refs/melange.wav

The number after `=` is the point (in seconds) at which to take the 10 s — aim
for a chorus or a drop, not an intro.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from aimc.audio import duration, install_hint, missing
from aimc.workspace import unique_path

SLOT_SECONDS = 10          # slot size, imposed by process_reference_audio
SLOTS = 3                  # three slots: start, middle, end
TOTAL_SECONDS = SLOT_SECONDS * SLOTS
SAMPLE_RATE = 48000        # what the engine expects
CHANNELS = 2

REQUIRED_TOOLS = ("ffmpeg", "ffprobe")

# A deviation of more than 50 ms over the 30 s breaks the deterministic slicing.
DURATION_TOLERANCE = 0.05

Source = tuple[Path, float]


def parse_source(spec: str, parser: argparse.ArgumentParser) -> Source:
    """Split 'path.mp3=45' into (path, offset). The offset is optional."""
    if "=" in spec:
        raw_path, _, raw_offset = spec.rpartition("=")
        try:
            offset = float(raw_offset)
        except ValueError:
            parser.error(f'unreadable offset in "{spec}" — expected: file.mp3=45')
        if offset < 0:
            parser.error(f'negative offset in "{spec}"')
    else:
        raw_path, offset = spec, 0.0

    path = Path(raw_path).expanduser()
    if not path.is_file():
        parser.error(f"file not found: {path}")
    return path, offset


def check_offsets(sources: list[Source], parser: argparse.ArgumentParser) -> None:
    """Check that each offset really does leave 10 s of material behind it."""
    for path, offset in sources:
        length = duration(path)
        if length is None:
            parser.error(f"cannot read the duration of {path} — is it a valid audio file?")
        if offset >= length:
            parser.error(f"offset {offset:g} s past the end of {path.name} "
                         f"({length:.1f} s)")
        if offset + SLOT_SECONDS > length:
            print(f"  warning: {path.name} only has {length - offset:.1f} s after "
                  f"{offset:g} s — the slot will be padded with silence", file=sys.stderr)


def extract_slot(path: Path, offset: float, dest: Path) -> None:
    """Take exactly SLOT_SECONDS starting at `offset`, in 48 kHz stereo.

    `apad` guarantees the full duration even when we land near the end of the
    track: a slot that came out short would shift every following one and break
    the deterministic slicing.
    """
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y",
         "-ss", f"{offset}", "-t", f"{SLOT_SECONDS}", "-i", str(path),
         "-af", f"apad=whole_dur={SLOT_SECONDS},aresample={SAMPLE_RATE}",
         "-ac", str(CHANNELS), "-ar", str(SAMPLE_RATE),
         "-c:a", "pcm_s16le", str(dest)],
        check=True, capture_output=True,
    )


def concat(slot_files: list[Path], out_path: Path, work_dir: Path) -> None:
    """Stitch the slots end to end, without re-encoding to anything but PCM."""
    listing = work_dir / "list.txt"
    listing.write_text("".join(f"file '{f.resolve()}'\n" for f in slot_files),
                       encoding="utf-8")
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0",
         "-i", str(listing), "-c:a", "pcm_s16le",
         "-ar", str(SAMPLE_RATE), "-ac", str(CHANNELS), str(out_path)],
        check=True, capture_output=True,
    )


def build(sources: list[Source], out_path: Path) -> None:
    """Fill the three slots cycling over the tracks given, and stitch them."""
    plan = [sources[i % len(sources)] for i in range(SLOTS)]
    work_dir = out_path.parent / ".blend_tmp"
    work_dir.mkdir(exist_ok=True)
    try:
        slot_files = []
        print(f"Building {TOTAL_SECONDS} s out of "
              f"{len(sources)} track(s):")
        for i, (path, offset) in enumerate(plan):
            dest = work_dir / f"slot{i}.wav"
            extract_slot(path, offset, dest)
            slot_files.append(dest)
            start = i * SLOT_SECONDS
            print(f"  [{start:2d}-{start + SLOT_SECONDS:2d} s]  {path.name} "
                  f"@ {offset:g} s")
        concat(slot_files, out_path, work_dir)
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="blend-refs",
        description="Blends several tracks into a single 30 s style reference.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""example:
  ./blend-refs ~/Music/a.mp3=45 ~/Music/b.mp3=30 ~/Music/c.mp3=12 -o refs/melange.wav
  ./song --preset presets/electro-house.json --reference refs/melange.wav --style-strength 0.25

Give 1 to 3 tracks. With fewer than 3, the slots are filled cyclically
(2 tracks -> A, B, A), which gives more weight to the first one.
""",
    )
    parser.add_argument("sources", nargs="+", metavar="FILE[=OFFSET]",
                        help="track and, after '=', the second at which to take the 10 s")
    parser.add_argument("-o", "--out", default="refs/melange.wav", metavar="FILE",
                        help="output file (default: refs/melange.wav)")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    absent = missing(*REQUIRED_TOOLS)
    if absent:
        parser.error(install_hint(absent))

    if len(args.sources) > SLOTS:
        parser.error(f"{len(args.sources)} tracks given, but there are only {SLOTS} "
                     f"slots of {SLOT_SECONDS} s. Keep {SLOTS} at most.")

    sources = [parse_source(s, parser) for s in args.sources]
    check_offsets(sources, parser)

    wanted = Path(args.out).expanduser()
    wanted.parent.mkdir(parents=True, exist_ok=True)
    out_path = unique_path(wanted)
    if out_path != wanted:
        print(f"  {wanted.name} already exists — writing to {out_path.name}\n")

    build(sources, out_path)

    final = duration(out_path)
    if final is None or abs(final - TOTAL_SECONDS) > DURATION_TOLERANCE:
        print(f"\nWARNING: output of {final}s instead of {TOTAL_SECONDS}s. "
              f"The slicing will not be deterministic.", file=sys.stderr)
        return 1

    print(f"\n{out_path}  ({final:.2f} s, {SAMPLE_RATE} Hz, stereo)")
    print(f"\n  ./song --preset presets/electro-house.json \\\n"
          f"         --reference {out_path} --style-strength 0.25")
    return 0


if __name__ == "__main__":
    sys.exit(main())
