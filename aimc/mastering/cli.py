"""./master — prepares a track for distribution.

    ./master songs/the-track.wav

What the script does:

  1. refuses a compressed source (a 128k MP3 does not become lossless again);
  2. measures the track (EBU R128);
  3. reports an abruptly cut ending, which the platforms reject;
  4. normalises in two passes towards the target (-14 LUFS, true peak -1 dBTP);
  5. adds silence at the head and at the tail;
  6. writes a 24-bit WAV, preserving the sample rate.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from aimc.audio import install_hint, missing, stream_info
from aimc.mastering.measure import measure, tail_amplitude, tail_is_clean
from aimc.mastering.render import RenderOptions, normalise
from aimc.mastering.report import Report
from aimc.mastering.targets import LOSSY, TAIL_MAX, TARGET_LRA, TARGET_LUFS, TARGET_TP
from aimc.workspace import unique_path

REQUIRED_TOOLS = ("ffmpeg", "ffprobe")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="master",
        description="Prepares a track for distribution (lossless WAV, calibrated loudness).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""examples:
  ./song --preset presets/electro-house.json --seed 1 --format wav   # lossless source
  ./master songs/the-track.wav                                     # -> *_master.wav
  ./master songs/the-track.wav --lufs -16 --head 2 --tail 3

Distributors require lossless (WAV/FLAC, 16 or 24 bit, 44.1 kHz or above).
An MP3 can NOT be converted back: it has to be regenerated with --format wav.
""",
    )
    parser.add_argument("source", help="audio file to master")
    parser.add_argument("-o", "--out", metavar="FILE",
                        help="output (default: <source>_master.wav)")
    parser.add_argument("--lufs", type=float, default=TARGET_LUFS, metavar="N",
                        help=f"target integrated loudness (default: {TARGET_LUFS})")
    parser.add_argument("--true-peak", type=float, default=TARGET_TP, metavar="N",
                        help=f"maximum true peak in dBTP (default: {TARGET_TP})")
    parser.add_argument("--head", type=float, default=1.0, metavar="SECONDS",
                        help="silence added at the start (default: 1)")
    parser.add_argument("--tail", type=float, default=2.0, metavar="SECONDS",
                        help="silence added at the end (default: 2)")
    parser.add_argument("--bits", type=int, default=24, choices=[16, 24],
                        help="WAV bit depth (default: 24)")
    parser.add_argument("--sample-rate", type=int, default=None, metavar="HZ",
                        help="output rate (default: the source's)")
    parser.add_argument("--flac", action="store_true",
                        help="write a FLAC instead of a WAV")
    parser.add_argument("--force", action="store_true",
                        help="master a compressed source anyway")
    parser.add_argument("--report", metavar="FILE",
                        help="also write the measurements as JSON to this file "
                             "(for the studio: read the numbers rather than "
                             "re-parsing the log line by line)")
    return parser


def describe_source(src: Path, info: dict[str, Any], report: Report) -> None:
    codec = info.get("codec_name", "?")
    rate = int(info.get("sample_rate", 48000))
    report["source"] = {"name": src.name, "codec": codec, "sample_rate": rate,
                        "channels": info.get("channels"),
                        "duration": info.get("duration")}
    print(f"\nSource: {src.name}")
    print(f"  {codec}, {rate} Hz, {info.get('channels', '?')} channels, "
          f"{info.get('duration', 0):.1f} s")


def refuse_lossy(codec: str, report: Report) -> None:
    """The refusal of a compressed source, with the only way out there is."""
    sys.stdout.flush()
    print(f'\n  STOP: "{codec}" is a lossy format.', file=sys.stderr)
    print("  Distributors require lossless, and converting an MP3 to WAV",
          file=sys.stderr)
    print("  restores nothing — the information was thrown away at encoding time.",
          file=sys.stderr)
    print("\n  Generate the same take again as lossless:", file=sys.stderr)
    print("    ./song --preset presets/... --seed <the seed> --format wav\n",
          file=sys.stderr)
    print("  (--force to override, for a listen only.)", file=sys.stderr)
    report["error"] = f"lossy source ({codec}): a master would not be publishable"
    report["lossy_source"] = True


def describe_measurements(stats: dict[str, Any], args: argparse.Namespace) -> None:
    print(f"  integrated  {float(stats['input_i']):>6.1f} LUFS   (target {args.lufs:g})")
    print(f"  true peak   {float(stats['input_tp']):>6.1f} dBTP   (max {args.true_peak:g})")
    print(f"  range       {float(stats['input_lra']):>6.1f} LU")


def inspect_source(src: Path, args: argparse.Namespace,
                   report: Report) -> dict[str, Any] | None:
    """Measure the source and say what it is worth. None if the measurement failed.

    The EBU pass, reading it, the state of the ending and what both record are
    never separated: it is a single step, with a single possible failure.
    """
    print("\nMeasuring (EBU R128)…")
    stats = measure(src)
    if stats is None:
        print("  measurement failed", file=sys.stderr)
        report["error"] = "EBU R128 measurement failed"
        return None
    describe_measurements(stats, args)

    tail = tail_amplitude(src)
    report["before"] = {"lufs": float(stats["input_i"]),
                        "true_peak": float(stats["input_tp"]),
                        "lra": float(stats["input_lra"]), "tail": tail,
                        "tail_clean": tail_is_clean(tail)}
    describe_tail(tail)
    return stats


def describe_tail(amplitude: float) -> None:
    if tail_is_clean(amplitude):
        print(f"  tail        clean (final amplitude {amplitude:.3f})")
        return
    print(f"\n  WARNING: the tail cuts off (amplitude {amplitude:.3f} over the")
    print("  last 50 ms). Platforms reject truncated endings.")
    print("  Trailing silence does not fix a cut-off phrase — better to generate")
    print("  again, or lengthen the [Outro] section of the lyrics.")


def target_path(src: Path, args: argparse.Namespace, report: Report) -> Path:
    """Where to write — never over an existing file."""
    suffix = ".flac" if args.flac else ".wav"
    wanted = (Path(args.out).expanduser() if args.out
              else src.with_name(src.stem + "_master" + suffix))
    wanted.parent.mkdir(parents=True, exist_ok=True)
    out = unique_path(wanted)
    if out != wanted:
        print(f"\n  {wanted.name} already exists — writing to {out.name}")
    report["out"] = {"name": out.name,
                     "renamed_from": wanted.name if out != wanted else None}
    return out


def describe_master(out: Path, args: argparse.Namespace, final: dict[str, Any],
                    after: dict[str, Any] | None, report: Report) -> None:
    print(f"\nMaster: {out}")
    print(f"  {final.get('codec_name')}, {final.get('sample_rate')} Hz, "
          f"{args.bits} bit, {final.get('duration', 0):.1f} s "
          f"({out.stat().st_size / 1e6:.1f} MB)")
    if after:
        print(f"  integrated  {float(after['input_i']):>6.1f} LUFS")
        print(f"  true peak   {float(after['input_tp']):>6.1f} dBTP")

    report["out"].update({
        "codec": final.get("codec_name"), "sample_rate": final.get("sample_rate"),
        "bits": args.bits, "duration": final.get("duration"),
        "size_mb": round(out.stat().st_size / 1e6, 1),
    })
    if after:
        report["after"] = {"lufs": float(after["input_i"]),
                           "true_peak": float(after["input_tp"]),
                           "lra": float(after["input_lra"])}


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    report = Report({"lufs": args.lufs, "true_peak": args.true_peak,
                     "lra": TARGET_LRA, "tail_max": TAIL_MAX})

    absent = missing(*REQUIRED_TOOLS)
    if absent:
        parser.error(install_hint(absent))

    src = Path(args.source).expanduser()
    if not src.is_file():
        parser.error(f"file not found: {src}")

    info = stream_info(src)
    if not info:
        report["error"] = f"unreadable: {src.name}"
        report.emit(args.report, 2)
        parser.error(f"cannot read {src} — is it a valid audio file?")

    describe_source(src, info, report)
    codec = info.get("codec_name", "?")
    if codec in LOSSY and not args.force:
        refuse_lossy(codec, report)
        return report.emit(args.report, 1)

    stats = inspect_source(src, args, report)
    if stats is None:
        return report.emit(args.report, 1)

    out_rate = args.sample_rate or int(info.get("sample_rate", 48000))
    out = target_path(src, args, report)
    opts = RenderOptions(lufs=args.lufs, true_peak=args.true_peak, head=args.head,
                         tail=args.tail, bits=args.bits, sample_rate=out_rate,
                         flac=args.flac)

    print(f"\nTwo-pass normalisation → {out.name}")
    failure = normalise(src, out, opts, stats)
    if failure is not None:
        print(f"  ffmpeg failed:\n{failure}", file=sys.stderr)
        report["error"] = f"ffmpeg failed: {failure[-300:]}"
        return report.emit(args.report, 1)

    final = stream_info(out)
    describe_master(out, args, final, measure(out), report)

    if int(final.get("sample_rate", 0)) != out_rate:
        print(f"\n  WARNING: output at {final.get('sample_rate')} Hz instead of "
              f"{out_rate} Hz.", file=sys.stderr)
        report["error"] = (f"output at {final.get('sample_rate')} Hz instead of "
                           f"{out_rate} Hz")
        return report.emit(args.report, 1)
    return report.emit(args.report, 0)


if __name__ == "__main__":
    sys.exit(main())
