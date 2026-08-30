"""The web interface: it shows the pipeline, it does not reimplement it.

    library/     what the studio knows about the takes on disk
    jobs         the processes launched, and the locks that keep them apart
    reconstruct  a manifest for an orphaned take, marked as such
    commands     the `./song` and `./master` lines to run
    api          the routes, which assemble everything above
    server       uvicorn

`./song` and `./master` remain the single source of truth: the studio only has
buttons.
"""
