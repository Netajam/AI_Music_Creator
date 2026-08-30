#!/usr/bin/env bash
# Builds this repo's rendering half on a rented Linux GPU (Colab and anything
# shaped like it). Idempotent: every step checks whether it is already done, so
# re-running it after a disconnect costs seconds rather than a second install.
#
# What is *not* here is the point. `engine/` and `engine/checkpoints/` are the
# two things `.gitignore` keeps out of the repository — an upstream clone and
# 11 GB of weights — and they are exactly the two things a fresh runtime lacks.
# Everything else travelled with the git clone. This script only fetches the
# two, in the order the README already documents for a Mac.
#
#   bash colab/setup.sh              # what the night queue needs (~8 GB)
#   bash colab/setup.sh --full       # every checkpoint, including the 1.7B LM
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FULL=0
for arg in "$@"; do
  case "$arg" in
    --full) FULL=1 ;;
    *) echo "unknown argument: $arg" >&2; exit 2 ;;
  esac
done

# Each step is timed, and the total is printed at the end. Ten minutes is worth
# optimising only once it is known which minutes they are — the guesses here are
# a 5 GB wheel download and an 8 GB weight download, and those want opposite
# fixes.
_run_start=$(date +%s); _step_name=""; _step_start=0; _timings=""

_close_step() {
  [[ -z "$_step_name" ]] && return 0
  local now; now=$(date +%s)
  _timings+="$(printf '  %-26s %4ds' "$_step_name" $((now - _step_start)))"$'\n'
}

step() {
  _close_step
  _step_name="$1"; _step_start=$(date +%s)
  printf '\n\033[1m▶ %s\033[0m\n' "$1"
}

timings() {
  _close_step
  printf '\n\033[1m▶ where the time went\033[0m\n%s' "$_timings"
  printf '  %-26s %4ds\n' "TOTAL" $(( $(date +%s) - _run_start ))
}

# ---------------------------------------------------------------------------
step "uv"
# The wrappers (./song, ./night/worker.sh) all run `uv run --project engine`, so
# uv is not an implementation detail we could swap for pip here: it is the
# interface. Installing it is what makes those wrappers work unchanged.
export PATH="$HOME/.local/bin:$PATH"
if command -v uv >/dev/null 2>&1; then
  echo "already installed: $(uv --version)"
else
  curl -LsSf https://astral.sh/uv/install.sh | sh
  echo "installed: $(uv --version)"
fi

# ---------------------------------------------------------------------------
step "engine/ — the ACE-Step 1.5 clone"
if [[ -d engine/.git ]]; then
  echo "already cloned: $(git -C engine rev-parse --short HEAD)"
else
  # --depth 1: the history of the engine is upstream's business. The exact
  # revision still lands in every take's manifest (aimc/provenance/), which is
  # the only place this repo ever needed it.
  git clone --depth 1 https://github.com/ace-step/ACE-Step-1.5.git engine
fi

# ---------------------------------------------------------------------------
step "dependencies (~5 GB: torch+cu128, transformers, nano-vllm)"
# -p 3.12 rather than whatever the host ships: the engine declares
# `requires-python = ">=3.11,<3.13"`, and a Colab image that has moved on to
# 3.13 would otherwise fail to resolve. uv fetches its own 3.12 in seconds.
# The lock file is upstream's, so this resolves to the same wheels a Linux
# CUDA box would get anywhere else.
if [[ -x engine/.venv/bin/python ]]; then
  echo "already built: $(engine/.venv/bin/python -V)"
fi
uv sync --project engine -p 3.12

# ---------------------------------------------------------------------------
step "checkpoints (~8 GB)"
# The README's recipe is `uv run acestep-download`, which pulls the whole main
# repo including the 1.7B LM. We reach for the same two repositories directly,
# because the default LM in aimc/generation/catalog.py is the 0.6B — the 1.7B
# is 3.5 GB that nothing in this repo asks for unless --full says so.
python3 -m pip install --quiet --upgrade "huggingface_hub[hf_transfer]"
HF_HUB_ENABLE_HF_TRANSFER=1 FULL="$FULL" python3 - <<'PY'
import os
from pathlib import Path

from huggingface_hub import snapshot_download

ckpt = Path("engine/checkpoints")
ignore = None if os.environ["FULL"] == "1" else ["acestep-5Hz-lm-1.7B/*"]

# The main repo's layout *is* the checkpoints/ layout: vae/, Qwen3-Embedding-0.6B/,
# acestep-v15-turbo/ land where the engine already looks for them.
snapshot_download("ACE-Step/Ace-Step1.5", local_dir=ckpt, ignore_patterns=ignore)
snapshot_download("ACE-Step/acestep-5Hz-lm-0.6B", local_dir=ckpt / "acestep-5Hz-lm-0.6B")
PY

# ---------------------------------------------------------------------------
timings

printf '\n\033[1m▶ ready\033[0m\n'
du -sh engine/checkpoints engine/.venv 2>/dev/null | sed 's/^/  /'
echo
echo "  ./song --preset presets/electro-house.json --seed 1"
echo "  ./night/worker.sh          # drains night/queue/, models loaded once"
