"""AI Music Creator's own code.

Seven domains, stacked bottom to top — each one only knows about those
below it:

    workspace          where the repo's files live
    audio/             the ffmpeg toolbox, no numpy and no model
    provenance/        the identity of a take: its fingerprint, its version
    analysis/          the structural analysis of a track
    mastering/         bringing a take up to distribution standards
    references/        building a style reference
    generation/        the call into the ACE-Step engine
    studio/            the web interface, which drives everything above

`engine/` is not part of it: it is an upstream clone, read and never modified.
"""
