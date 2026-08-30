#!/usr/bin/env bash
# Wrapper: runs the night worker inside the engine's uv environment, the same
# way ./song does. VIRTUAL_ENV is cleared so an activated env cannot shadow it.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
unset VIRTUAL_ENV
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
exec uv run --project "$ROOT/engine" --no-sync python night/batch_render.py "$@"
