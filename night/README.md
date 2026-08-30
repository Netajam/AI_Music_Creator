# The night run

One hundred songs, written and rendered in one pass, unattended.

This folder holds the machinery. What it renders lives in the workspace —
`songs/night/` for the takes, `lyrics/night/` for the words, `presets/night/`
for the settings, one folder per collection in each — which is this repo when
there is nothing else, and the private clone when there is. See
[`colab/README.md`](../colab/README.md).

---

## What it is made of

| Path | What it does |
|---|---|
| `collections/<name>.py` | one collection: its metadata and its ten songs, lyrics included |
| `build.py` | turns a collection into lyrics files, presets and queued jobs — and refuses the ones that break a rule |
| `runner.sh` | drains `queue/` one take at a time and writes the ledger |
| `queue/` `done/` `failed/` | a job file moves between these three; its name fixes the order |
| `logs/<slug>.log` | the full engine log of that take |
| `ledger.tsv` | one line per finished take: when, how long, and what landed |

A song is added by editing a collection module and re-running `build.py`; a song
already rendered is skipped, so a collection can grow while the runner works.

```bash
python3 night/build.py neon-sud        # write files, queue what is new
./night/runner.sh                      # drain the queue, one process per take
```

---

## Why the runner looks slow on purpose

Loading the DiT and the 5Hz LM costs about three and a half minutes, and a
separate process per take pays it a hundred times — five and a half hours of
loading the same two checkpoints. The obvious fix is to hold the models in
memory and loop.

**It was built, measured, and reverted.** On this 16 GiB machine the second
process to hold a DiT drove swap to 15.5 GiB of 16, and the take hung at
`[DCW] Built DWT1D` for fifty minutes without ever failing — no error, no
traceback, the process alive at 9% CPU waiting on paging. The loading time is
what buys the machine back. `batch_render.py` is kept beside this file as the
record of the attempt; it is not what runs **here**. On a rented GPU it is
exactly what runs, because what beat it was a memory ceiling and not a design
fault — see [`colab/README.md`](../colab/README.md).

`--mlx-dit` was measured too, and is not available here for the same reason: it
loads the MLX weights *in addition to* the PyTorch ones and dies at
`MPS allocated: 11.76 GiB, other allocations: 8.95 GiB` against a 20.13 GiB
ceiling. That failure at least is loud.

## Why the runner does not trust exit codes

`./song` is documented to exit 0 after an out-of-memory that wrote nothing. A
take counts as `ok` here only when **both** hold: the engine printed `Done:`,
and a `.wav` exists that is newer than a marker file dropped the instant the
take was launched. A watchdog kills anything still running after thirty minutes,
because a night has room for a slow take and no room for a hung one.

## What `build.py` refuses

Each of these cost somebody a seven-minute take before it was written down in
[`docs/recipes.md`](../docs/recipes.md); here they cost two seconds.

- a `--style` of 512 characters or more — rejected by the CLI, but only after the preset has loaded;
- any section tag outside the eight the model actually reads, and any invented
  bracketed cue, which it treats as a section of its own rather than as a stage direction;
- a chorus that is not identical word for word between passes;
- fewer than five or more than eleven sections;
- a lyric density outside 3.5–12 characters per second.
