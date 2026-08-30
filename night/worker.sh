#!/usr/bin/env bash
# Wrapper: runs the night worker inside the engine's uv environment, the same
# way ./song does. VIRTUAL_ENV is cleared so an activated env cannot shadow it.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
unset VIRTUAL_ENV
# MPLBACKEND likewise. A Jupyter kernel exports
# `module://matplotlib_inline.backend_inline`, which lives in *its* Python and
# not in engine/.venv, and matplotlib raises at import rather than falling back
# — taking the whole run down from inside lightning -> torchmetrics, which no
# part of this repo asked for. Nothing here plots, so Agg settles it.
export MPLBACKEND=Agg
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
exec uv run --project "$ROOT/engine" --no-sync python night/batch_render.py "$@"
