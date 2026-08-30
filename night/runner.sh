#!/usr/bin/env bash
# The night runner: drains night/queue/, one take per process.
#
# One process per take is not an accident and not laziness. The obvious
# optimisation — hold the models in memory and loop — was built, measured and
# reverted: on 16 GiB the second process to hold a DiT drove swap to 15.5 GiB of
# 16 and a take hung for fifty minutes at `[DCW] Built DWT1D` without ever
# failing. Paying three and a half minutes of loading per take is what buys the
# machine back. See docs/recipes.md.
#
# `./song` exits 0 even when it failed, so success is decided by a file newer
# than a marker dropped at launch, and by the engine's own "Done:".
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# The content half of the tree. This repeats `_workspace` in aimc/workspace.py
# by hand — a shell script cannot import it, and this is the only one of the
# wrappers that needs to know, because every other one reaches the content
# through Python. Keep the two in step.
WS="$ROOT"
if [[ -n "${AIMC_WORKSPACE:-}" ]]; then
  WS="$AIMC_WORKSPACE"
elif [[ -f "$ROOT/.workspace" ]]; then
  WS="$ROOT/$(cat "$ROOT/.workspace")"
fi

Q="$WS/night/queue"; DONE="$WS/night/done"; FAIL="$WS/night/failed"
LOGS="$WS/night/logs"
LEDGER="$WS/night/ledger.tsv"
MAX_SECONDS=1800   # a take that has not finished by then is hung, not slow
[[ -f "$LEDGER" ]] || printf 'finished_at\tslug\tcollection\tstatus\tseconds\taudio\tlog\n' > "$LEDGER"

get() { python3 -c "import json,sys;print(json.load(open(sys.argv[1])).get(sys.argv[2],''))" "$1" "$2"; }

while :; do
  job="$(ls "$Q"/*.json 2>/dev/null | sort | head -1)"
  [[ -z "$job" ]] && { echo "queue empty — runner stops at $(date '+%F %T')"; exit 0; }

  slug="$(get "$job" slug)";   coll="$(get "$job" collection)"
  preset="$(get "$job" preset)"; seed="$(get "$job" seed)"
  steps="$(get "$job" steps)"; extra="$(get "$job" extra)"
  outdir="$WS/songs/night/$coll"; log="$LOGS/$slug.log"
  mkdir -p "$outdir" "$LOGS"

  echo "▶ $(date '+%F %T')  $coll/$slug  (seed $seed, steps $steps)"
  start=$(date +%s)
  marker="$outdir/.started-$slug"; : > "$marker"

  # shellcheck disable=SC2086
  ./song --preset "$WS/$preset" --seed "$seed" --steps "$steps" --out "$outdir" $extra \
      > "$log" 2>&1 &
  song_pid=$!
  # A hung take must not eat the night: watch it, and cut it loose past the cap.
  ( sleep "$MAX_SECONDS"; kill -9 "$song_pid" 2>/dev/null ) & watchdog=$!
  wait "$song_pid" 2>/dev/null
  kill "$watchdog" 2>/dev/null; wait "$watchdog" 2>/dev/null

  end=$(date +%s); secs=$((end-start))
  audio="$(find "$outdir" -name '*.wav' -newer "$marker" 2>/dev/null | sort | tail -1)"
  audio="${audio#"$WS"/}"
  rm -f "$marker"; rm -rf "$outdir"/.run-* 2>/dev/null

  if [[ -n "$audio" && -s "$audio" ]] && grep -q '^Done:' "$log"; then
    status=ok; mv "$job" "$DONE/"
  else
    status=FAILED; mv "$job" "$FAIL/"
    echo "  ✗ failed after ${secs}s — tail of $log:" >&2
    grep -viE "\| (INFO|DEBUG) " "$log" | tail -4 >&2
  fi
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
     "$(date '+%F %T')" "$slug" "$coll" "$status" "$secs" "$audio" "$log" >> "$LEDGER"
  echo "  $status  ${secs}s  ${audio:-(nothing written)}"
done
