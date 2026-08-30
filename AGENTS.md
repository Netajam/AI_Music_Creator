# AI Music Creator

AI song generation, 100% local, on a MacBook M2 Pro (16 GB).
See [README.md](README.md) for installation and usage, and
[BEGINNERS-GUIDE.md](BEGINNERS-GUIDE.md) to get started.

`engine/` is a clone of the upstream [ACE-Step 1.5](https://github.com/ace-step/ACE-Step-1.5) repository.
It is not our own code: do not modify it, do not open issues against it, and
ignore its `engine/AGENTS.md`, which belongs to the upstream project.

## Language

Everything written in this repository is in English: documentation, docstrings,
comments, commit messages, issue notes, and user-facing strings. The two
exceptions are `lyrics/` and `presets/`, which hold the creative content —
French song lyrics and generation prompts — and stay in the language they are
sung in.

## Where the code lives

All of our own code is in the `aimc/` package; the commands at the repository
root (`song`, `studio`, `analyse`, `master`, `grab`, `blend-refs`) are one-line
wrappers. The domains stack up, and each one only knows about those below it:
`workspace` and `audio/` at the base, then `provenance/`, `analysis/`,
`mastering/`, `references/`, then `generation/`, and `studio/` on top of
everything. See the "Structure" section of the README.

Three rules hold this stack together, and `./check` verifies them
(`tools/check_layers.py`) because they break silently — a domain only knows
about those below it, plus the two rules below:

- **`acestep` is only imported inside `aimc/generation/render/`** (`engine.py`
  and `params.py`), and always *inside* a function, so only once the arguments
  have been validated. Hoisting one of these imports to the top of a module
  would make `--help` slow and reserve memory for nothing.
- **`audio/`, `mastering/` and `references/` do not import numpy.** `./master`,
  `./grab` and `./blend-refs` run under the system python3, where numpy does not
  exist; adding a numpy import there breaks all three.

## Checking your work

`./check` runs ruff, mypy, then the architecture check on our own modules
(`engine/` is excluded).
Run it before handing in a Python change. `./check --fix` first fixes what ruff
knows how to fix. The settings are in `pyproject.toml`, and the README explains
the strictness level we settled on.

## Agent skills

### Issue tracker

Issues live as markdown files under `.scratch/<feature-slug>/` in this repo. See `docs/agents/issue-tracker.md`.

### Triage labels

The five canonical triage roles, unchanged: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.
