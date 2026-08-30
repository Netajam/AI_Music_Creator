"""The call into the ACE-Step engine: from the command line to a take on disk.

    catalog   what the engine can do, copied here to keep --help fast
    command/  the command line, up to a validated intent
    render/   the intent, up to an audio file and its manifest
    cli       main(): one then the other

The boundary between the two is the boundary of the heavy imports. All of
`command/` runs without torch or acestep; `render/engine` is the only module in
the repo that imports the engine, and it only does so once the arguments have
been validated.
"""
