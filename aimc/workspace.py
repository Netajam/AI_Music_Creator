"""Where the repo's files live, and how never to overwrite one.

A single place knows the tree. When these paths were recomputed in every
module, moving a file meant tracking down every copy of
`Path(__file__).resolve().parent`, and missing a single one was enough for one
tool to write somewhere the others did not look.

That single place is also what lets the tree be in two pieces. The tool half —
this package, the wrappers, the night machinery — is public and holds no song
anyone wrote. The content half — presets, lyrics, references, takes — is
private and arrives as a second clone. Everything below the `WORKSPACE` line
belongs to the second; everything above it to the first.
"""

from __future__ import annotations

import os
from pathlib import Path

# aimc/workspace.py -> aimc/ -> the repo root.
REPO_ROOT = Path(__file__).resolve().parent.parent
PACKAGE_ROOT = REPO_ROOT / "aimc"

# `engine/` is the upstream ACE-Step clone: we read the weights and the
# `acestep` package from it, we never write to it.
ENGINE_ROOT = REPO_ROOT / "engine"
CHECKPOINT_DIR = ENGINE_ROOT / "checkpoints"


def _workspace() -> Path:
    """The content half of the tree: what to generate, and what came out.

    Three answers, in order:

      * `AIMC_WORKSPACE`, for one command that should look somewhere else;
      * `.workspace` at the repo root — one line, a path, not versioned — for a
        machine that always should;
      * the repo itself.

    The third is not a fallback. It is the ordinary case for anyone who clones
    the public repo: `presets/`, `lyrics/` and `songs/` sit at the root, the
    README's commands run, and nothing has to be configured before the first
    song. The first two exist for the machine that also has the private half,
    and they are the only thing that machine has to say to reach it.
    """
    env = os.environ.get("AIMC_WORKSPACE")
    if env:
        return Path(env).expanduser().resolve()
    marker = REPO_ROOT / ".workspace"
    if marker.exists():
        # Read relative to the repo, so the file says the same thing whatever
        # directory the command was run from and wherever the repo was cloned.
        return (REPO_ROOT / marker.read_text().strip()).resolve()
    return REPO_ROOT


WORKSPACE = _workspace()

SONGS = WORKSPACE / "songs"
PRESETS = WORKSPACE / "presets"
LYRICS = WORKSPACE / "lyrics"
REFS = WORKSPACE / "refs"

# The night's own bookkeeping — the queue, the ledger, the collection modules —
# is content, not machinery: `night/*.py` is public and what it is asked to
# render is not. When the workspace is the repo, the two share one folder,
# which is what they did before there were two repos at all.
NIGHT = WORKSPACE / "night"

# Tracks fetched by `./grab`, and the moments we decided to keep in them. The
# two are separated on purpose, and `.gitignore` tells them apart: the audio is
# under copyright and never enters the repository, while a pick is a few hundred
# bytes of our own decision — the one thing here that cannot be downloaded again.
DOWNLOADS = REFS / "downloads"
PICKS = REFS / "picks"

CACHE = WORKSPACE / ".studio-cache"

AUDIO_EXT = {".wav", ".mp3", ".flac", ".opus", ".aac"}
LOSSLESS_EXT = {".wav", ".flac"}


def unique_path(path: Path) -> Path:
    """Return a free path: appends -2, -3… if the file already exists.

    We never overwrite an existing file silently. On the generation side the
    reason is stronger still: the engine names its outputs after a hash of the
    parameters (`generate_uuid_from_params`, "Same parameters will always
    generate the same UUID"), so re-running an identical generation would aim
    at exactly the previous take's file.
    """
    if not path.exists():
        return path
    stem, suffix, parent = path.stem, path.suffix, path.parent
    n = 2
    while True:
        candidate = parent / f"{stem}-{n}{suffix}"
        if not candidate.exists():
            return candidate
        n += 1
