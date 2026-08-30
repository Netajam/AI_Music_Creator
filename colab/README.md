# Renting a GPU

The 16 GiB in the README's memory section is the constraint every decision in
this repo was made against: the 2B DiT rather than the 4B, the 0.6B LM rather
than the 1.7B, one take at a time, and `night/runner.sh` paying three and a half
minutes of model loading *per take* because holding a DiT across takes drove the
machine into swap.

Colab lifts exactly that one constraint and nothing else. The songs, the
presets, the lyrics and the render path are identical — the manifest beside a
take rendered here says the same things, except for the device.

```
colab/
  AI_Music_Creator.ipynb   the notebook: open it in Colab
  setup.sh                 what it runs to build engine/ and the checkpoints
```

## The two halves

This repository is the tool. It holds no preset anyone wrote and no take anyone
rendered, and a clone of it is complete on its own: the examples in `presets/`
run, and you can write your own beside them.

The songs are a second repository, private, cloned into `private/`. One line —
`.workspace`, not versioned, containing `private` — is what tells the tool to
look there:

| `.workspace` | `PRESETS` resolves to | who |
|---|---|---|
| absent | `presets/` | anyone who clones this repo |
| `private` | `private/presets/` | the machine that also has the songs |

`_workspace` in `aimc/workspace.py` is the whole of it, and `AIMC_WORKSPACE`
overrides it for a single command. Nothing else in the tool knows there are two
repositories: `SONGS`, `PRESETS`, `LYRICS`, `REFS` and `NIGHT` all hang off that
one answer, which is why a preset saying `../../../lyrics/night/…` and a job file
saying `presets/night/…` keep meaning what they meant — the whole content tree
moves together, so the paths inside it never change.

Step 4 of the notebook is the only place this matters: it clones the private
repo and writes that line. Skip it and the notebook renders the examples.

Open the notebook at
<https://colab.research.google.com/github/YOUR-USERNAME/AI_Music_Creator/blob/main/colab/AI_Music_Creator.ipynb>,
set the runtime to GPU, and run the cells in order.

---

## What actually differs

**`night/batch_render.py` runs, and `night/runner.sh` does not.** The worker that
loads the models once and walks the queue was built for the Mac, measured, and
reverted — see the header of `night/README.md`. Its failure there was a memory
ceiling, not a design fault, and on a rented card the ceiling is gone. Over 75
takes it saves about four and a half hours of loading the same two checkpoints.

**The machine gets the last word on two settings.** The notebook passes them to
every job through the worker's `--extra`:

| | why |
|---|---|
| `--device cuda` | detection would otherwise have to guess |
| `--backend pt` *(pre-Ampere only)* | nano-vllm wants bfloat16, which starts at compute capability 8.0; on a T4 at 7.5 the engine would try, fail, and fall back to PyTorch anyway |

A job that already says something in its own `extra` keeps saying it: the
machine's arguments are appended, so they only settle what the song left open.

**Nothing comes back through git.** `songs/` is gitignored and stays that way.
The notebook copies takes to Drive as they land, which also means a disconnect
costs the take in flight and nothing more. What is worth committing on the Mac
afterwards is `night/ledger.tsv` and the job files that moved into `night/done/`
— the record of what was rendered, and the only part of a run that re-running
cannot reproduce.

---

## What setup.sh fetches, and what it does not

`.gitignore` keeps two things out of this repository, and they are precisely the
two a fresh runtime lacks:

| | | |
|---|---|---|
| `engine/` | the upstream ACE-Step 1.5 clone, `--depth 1` | ~5 GB once `uv sync` has run |
| `engine/checkpoints/` | `ACE-Step/Ace-Step1.5` + `ACE-Step/acestep-5Hz-lm-0.6B` | ~8 GB |

Everything else arrived with the `git clone`.

The 1.7B LM is skipped unless `--full` asks for it: `aimc/generation/catalog.py`
defaults to the 0.6B, and no preset in this repo overrides it, so the 3.5 GB
would be downloaded for nothing.

The script pins Python 3.12 (`uv sync -p 3.12`) because the engine declares
`requires-python = ">=3.11,<3.13"` and a Colab image that has moved on to 3.13
would fail to resolve. It is idempotent: after a reconnect, re-running it checks
rather than reinstalls.

---

## Setup is paid once per machine, not once

Ten minutes of install and download, every time Colab gives you a new runtime,
and it will. That is the standing cost of not owning the card. A batch worth
sending is one that is long enough to earn it back — which the night queue,
being seventy-five takes, comfortably is, and one experimental take is not.

For one take, the Mac is still the shorter path.
