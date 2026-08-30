"""The name of a take on disk."""

from __future__ import annotations

import argparse
from pathlib import Path


def final_name(args: argparse.Namespace, source: Path, stamp: str) -> str:
    """A readable name: <preset>-seed<N>-<timestamp>.<ext>

    A derived take keeps the name of the take it came from, plus what was done
    to it: `<source>+guitar-<timestamp>.wav`. Without that, adding a track would
    look like a brand-new take in the folder.
    """
    if args.lego:
        base = Path(args.lego).stem
        # avoids `take+guitar+guitar+guitar` after successive additions
        return f"{base}+{args.lego_track}-{stamp}{source.suffix}"
    base = Path(args.preset).stem if args.preset else "song"
    seed = args.seed if args.seed >= 0 else "rnd"
    return f"{base}-seed{seed}-{stamp}{source.suffix}"
