"""The structural analysis of a track: sections, tempo, vocals, drops.

Everything here is computed by signal processing, with no model: these are
estimates, not ground truth. The weak spots are flagged in each function — it
is better to know what you cannot rely on.

    spectral   decoding and spectrogram, the foundation
    tempo      autocorrelation of the spectral flux
    sections   boundaries and labels
    voice      vocal presence and incoming bass
    track      the assembly: `analyse()`
    render     the terminal formatting

Three exceptions, all of which load a model and are therefore never run on their
own initiative — they are asked for, and they say what they cost:

    lyrics     forced alignment: where each line is sung
    stems      separation: which of drums, bass, vocals and other actually play
    tags       naming what plays inside `other`, and the genre of the mix

`tags` rides along inside `stems`' pass rather than making one of its own: the
stem it reads only exists in there. What it can honestly claim is narrower than
a name, and its docstring is where that is set out.
"""

from aimc.analysis.track import analyse

__all__ = ["analyse"]
