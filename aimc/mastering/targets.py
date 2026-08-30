"""What we aim for, and the rule that says whether a take can ship.

The thresholds and the rule live together, in a single place. The studio imports
them rather than copying them: two definitions of the word "publishable" would
drift apart, and the interface would end up promising something other than what
`./master` actually accepts.
"""

from __future__ import annotations

from typing import Any

# Codec names as ffprobe returns them. Not to be confused with the format names
# of `./song --format`, which describe the same loss on the generation side.
LOSSY = {"mp3", "aac", "opus", "vorbis", "wmav2"}

TARGET_LUFS = -14.0        # the streaming platforms' target
TARGET_TP = -1.0           # true peak, in dBTP
TARGET_LRA = 11.0

# Peak amplitude tolerated over the last 50 ms. Beyond it, the track stops
# dead: the platforms reject truncated endings, and trailing silence does not
# repair a cut-off phrase.
TAIL_MAX = 0.02
TAIL_WINDOW = 0.05

# Deviation from the target loudness still considered "on target". A take never
# lands exactly on -14.0, and demanding exactness would fail tracks that are
# perfectly distributable.
LUFS_TOLERANCE = 1.0


def _lossy_refusal(codec: str | None) -> dict[str, Any] | None:
    """The verdict on a compressed source, which no other criterion redeems."""
    if codec is None or codec not in LOSSY:
        return None
    # Nothing else counts: no master recovers a lossy encoding.
    return {"ready": False, "lossless": False,
            "missing": [f"lossy format ({codec}) — not publishable, "
                        f"it has to be generated again as lossless"],
            "unknown": []}


def _loudness_gap(lufs: float | None, target: float) -> str | None:
    if lufs is None or abs(lufs - target) <= LUFS_TOLERANCE:
        return None
    return f"{lufs:+.1f} LUFS, target {target:+.0f} (±{LUFS_TOLERANCE:g})"


def _peak_excess(true_peak: float | None, target: float) -> str | None:
    if true_peak is None or true_peak <= target:
        return None
    return f"true peak {true_peak:+.1f} dBTP, ceiling {target:+.0f}"


def _tail_cut(tail: float | None) -> str | None:
    if tail is None or tail <= TAIL_MAX:
        return None
    return f"tail cut off (amplitude {tail:.3f}, ceiling {TAIL_MAX:g})"


def publishable(codec: str | None, lufs: float | None, true_peak: float | None,
                tail: float | None, lufs_target: float = TARGET_LUFS,
                tp_target: float = TARGET_TP) -> dict[str, Any]:
    """"Can this one ship?"

    Every missing criterion is returned with its measured value and its target: a
    badge that only says "no" helps nobody choose between mastering and
    regenerating.

    An unmeasured criterion goes into `unknown` and not into `missing`: "we do
    not know" is not "this is wrong", but it is not enough to publish either.
    """
    refusal = _lossy_refusal(codec)
    if refusal is not None:
        return refusal

    unknown = [label for value, label in (
        (codec, "format unknown"),
        (lufs, "loudness not measured"),
        (true_peak, "true peak not measured"),
        (tail, "tail not measured"),
    ) if value is None]

    missing = [issue for issue in (
        _loudness_gap(lufs, lufs_target),
        _peak_excess(true_peak, tp_target),
        _tail_cut(tail),
    ) if issue]

    return {"ready": not missing and not unknown, "lossless": True,
            "missing": missing, "unknown": unknown}
