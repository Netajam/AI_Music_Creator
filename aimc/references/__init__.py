"""Building a style reference: grab tracks, keep 30 s of them.

    grab    downloads a track from YouTube / YouTube Music
    blend   cuts three 10 s slots out of them for the engine's conditioning
    picks   the moments we decided to keep, and what we heard in them

Both commands run under the system python3: no numpy and no acestep here.
"""
