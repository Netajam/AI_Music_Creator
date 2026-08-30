"""./song — generates a song with ACE-Step 1.5, locally, on Apple Silicon.

Three modes:

  * text -> music         : a written style + French lyrics
  * style reference       : the same, but steered by an existing track
                            (a new song "in the same spirit")
  * cover                 : re-records an existing track in another style

Every option can come from a JSON preset (--preset); the arguments passed on the
command line override the preset.

The heavy imports (torch, acestep) live in `engine.py` and are only done once
the arguments have been validated, so that --help and validation stay instant
and reserve no memory.
"""

from __future__ import annotations

import sys

from aimc.generation.command import (
    apply_preset,
    build_parser,
    inherit_from_source,
    resolve_lyrics,
    validate,
)
from aimc.generation.render import describe, resolve_backend, run


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    apply_preset(args, parser)
    inherit_from_source(args)
    validate(args, parser)
    lyrics = resolve_lyrics(args, parser)

    if args.dry_run:
        # Nothing is loaded, so nothing can be detected: we announce the choice
        # that would be made rather than presenting it as an observation.
        device = args.device if args.device != "auto" else "mps (assumed)"
        describe(args, lyrics, device, resolve_backend(args.backend, "mps"))
        print("  --dry-run: nothing was loaded and nothing was generated.\n")
        return 0

    return run(args, lyrics)


if __name__ == "__main__":
    sys.exit(main())
