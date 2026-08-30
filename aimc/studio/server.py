"""./studio — a web interface to drive and inspect generations.

    ./studio          then  http://127.0.0.1:8000

This is not ACE-Step's Gradio interface (`./ui`), which knows nothing about this
repo. This one shows *our* pipeline: the presets, the lyrics, the references
built with blend-refs, the takes already produced with the exact settings that
created them, and the energy profile of each track so you can spot where to
touch it up.

It does not reimplement generation: it calls `./song`, which remains the single
source of truth. And it refuses to start a generation while another one is
running — two simultaneous generations exhaust the 16 GB and make both fail.
"""

from __future__ import annotations

import os
import sys

import uvicorn

from aimc.studio.api import INDEX, app

DEFAULT_PORT = 8000


def main() -> int:
    if not INDEX.exists():
        print(f"{INDEX.name} missing next to api.py", file=sys.stderr)
        return 1
    port = int(os.environ.get("STUDIO_PORT", str(DEFAULT_PORT)))
    print(f"\n  Studio  ->  http://127.0.0.1:{port}\n")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
    return 0


if __name__ == "__main__":
    sys.exit(main())
