"""From the command line to a validated intent, without loading anything heavy.

    options      the 45 options, one group per purpose
    presets      a JSON preset gives the defaults, the CLI keeps the last word
    inheritance  what a derived take carries over from its source
    validation   refuse early, before the slightest engine import
    lyrics       a file, some text, or instrumental

Nothing here imports `acestep` or numpy: `--help` and a rejected argument have
to stay instant and reserve no memory.
"""

from aimc.generation.command.inheritance import inherit_from_source
from aimc.generation.command.lyrics import resolve_lyrics
from aimc.generation.command.options import build_parser
from aimc.generation.command.presets import apply_preset
from aimc.generation.command.validation import validate

__all__ = ["apply_preset", "build_parser", "inherit_from_source", "resolve_lyrics", "validate"]
