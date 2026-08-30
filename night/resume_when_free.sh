#!/usr/bin/env bash
# Waits for the machine to be free, then drains the queue.
#
# On 16 GiB, two memory-hungry jobs do not share: measured, one take went from
# 9 minutes to 102 while another audio-analysis pipeline was running, and that
# pipeline slowed to over two hours per track at the same time. Serialising is
# strictly better for both, so this waits rather than competing.
#
# It gives up waiting after MAX_WAIT and starts anyway — the songs were asked
# for, and a slow take beats no take.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"
FOREIGN='analyse\.ts|measure\.py'
MAX_WAIT=${MAX_WAIT:-14400}      # 4 hours
INTERVAL=120
waited=0; clear_streak=0
while (( waited < MAX_WAIT )); do
  if pgrep -f "$FOREIGN" >/dev/null 2>&1; then
    clear_streak=0
  else
    clear_streak=$((clear_streak + 1))
    # two consecutive clear checks, so we don't start between two of its tracks
    if (( clear_streak >= 2 )); then
      echo "machine free after ${waited}s — starting the render at $(date '+%F %T')"
      exec ./night/runner.sh
    fi
  fi
  sleep "$INTERVAL"; waited=$((waited + INTERVAL))
done
echo "still busy after ${MAX_WAIT}s — starting anyway at $(date '+%F %T')"
exec ./night/runner.sh
