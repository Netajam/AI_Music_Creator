# Issue tracker: Local Markdown

Issues and PRDs for this repo live as markdown files in `.scratch/`.

This repo has no GitHub remote (it is not currently a git repository at all), so
there is no `gh` CLI workflow. Do not try to create GitHub issues.

## Conventions

- One feature per directory: `.scratch/<feature-slug>/`
- The PRD is `.scratch/<feature-slug>/PRD.md`
- Implementation issues are `.scratch/<feature-slug>/issues/<NN>-<slug>.md`, numbered from `01`
- Triage state is recorded as a `Status:` line near the top of each issue file (see `triage-labels.md` for the role strings)
- Comments and conversation history append to the bottom of the file under a `## Comments` heading

## When a skill says "publish to the issue tracker"

Create a new file under `.scratch/<feature-slug>/` (creating the directory if needed).

## When a skill says "fetch the relevant ticket"

Read the file at the referenced path. The user will normally pass the path or the issue number directly.

## Repo-specific notes

- **Never file issues against `engine/`.** It is a vendored clone of the upstream
  ACE-Step 1.5 repository, not code maintained here. Problems that trace back to
  the engine belong upstream, or in an issue about how *this* project calls it.
- **`.scratch/` is versioned, not ignored.** If this project ever gets a git repo,
  the issues are the tracker — losing them to `.gitignore` would lose the work log.
  Do not add `.scratch/` to `.gitignore`.
- The tracked code is the `aimc/` package — `workspace.py` plus the `audio`,
  `provenance`, `analysis`, `mastering`, `references`, `generation` and `studio`
  domains — and the one-line wrapper scripts at the root (`song`, `studio`,
  `analyse`, `master`, `grab`, `blend-refs`), plus `presets/`, `lyrics/`, and
  `refs/`.
