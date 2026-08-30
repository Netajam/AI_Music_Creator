"""What the engine can do, copied here so `--help` stays instant.

Importing `acestep.constants` would load the whole package — and therefore torch
— just to print a help message or reject an argument. So these lists are copied
here, and `engine.run` revalidates them against the engine's own at the moment
it loads it for real.
"""

from __future__ import annotations

# Copied from engine/acestep/constants.py: TRACK_NAMES.
TRACK_NAMES = [
    "woodwinds", "brass", "fx", "synth", "strings", "percussion",
    "keyboard", "guitar", "bass", "drums", "backing_vocals", "vocals",
]

# Listening formats: producible, but never publishable. Mastering refuses them
# at the door (its `LOSSY` list is in codec names as ffprobe sees them; here
# they are the names of --format). A take born in one of these formats is
# permanently lost to distribution: the information is thrown away at encoding
# time, and no conversion invents it back.
LOSSY_FORMATS = {"mp3", "opus", "aac"}

AUDIO_FORMATS = ["mp3", "wav", "flac", "wav32", "opus", "aac"]

# The 0.6B is the only LM that leaves headroom next to the 2B DiT in float32 on
# a 16 GB machine. See engine/.env.
DEFAULT_LM = "acestep-5Hz-lm-0.6B"
DEFAULT_DIT = "acestep-v15-turbo"

# Bounds accepted on the command line, kept next to what they describe.
BPM_RANGE = (30, 300)
DURATION_RANGE = (10, 600)
STYLE_MAX_CHARS = 512
