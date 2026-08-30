"""From the validated intent to a take on disk.

    runtime   compute device and language-model backend
    summary   the recap printed before launching, and all of `--dry-run`
    params    CLI arguments -> engine parameters, one mode per function
    naming    the name of a take on disk
    manifest  the settings file written next to it
    engine    the bridge to acestep: the only module in the repo that imports it
"""

from aimc.generation.render.engine import run
from aimc.generation.render.runtime import resolve_backend
from aimc.generation.render.summary import describe

__all__ = ["describe", "resolve_backend", "run"]
