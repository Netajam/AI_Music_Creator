"""Where the lyrics come from: a file, some text, or nothing at all."""

from __future__ import annotations

import argparse
from pathlib import Path

INSTRUMENTAL = "[Instrumental]"


# RET503 is silenced below: parser.error() is typed NoReturn in typeshed — mypy
# knows it and accepts the function as-is, but ruff does not follow library
# NoReturns and believes there is an implicit fall-through at the end of the
# function. Adding a return after parser.error() would be dead code.
def resolve_lyrics(args: argparse.Namespace,  # noqa: RET503
                   parser: argparse.ArgumentParser) -> str:
    if args.instrumental:
        return INSTRUMENTAL
    if args.lyrics_text:
        return str(args.lyrics_text)
    if args.lyrics:
        path = Path(args.lyrics).expanduser()
        if not path.is_file():
            parser.error(f"lyrics file not found: {path}")
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            parser.error(f"lyrics file is empty: {path}")
        return text
    parser.error("one of --lyrics, --lyrics-text or --instrumental is required")
