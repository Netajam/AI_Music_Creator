# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

This is a **single-context** repo: one `CONTEXT.md` and one `docs/adr/`, both at the root.

## Before exploring, read these

- **`CONTEXT.md`** at the repo root — the domain glossary
- **`docs/adr/`** — read ADRs that touch the area you're about to work in

If any of these files don't exist, **proceed silently**. Don't flag their absence; don't suggest creating them upfront. The producer skill (`/grill-with-docs`) creates them lazily when terms or decisions actually get resolved.

As of this file's creation, neither exists yet. That is the expected starting state.

## File structure

```
/
├── CONTEXT.md              ← the domain glossary
├── docs/
│   ├── adr/
│   │   ├── 0001-….md
│   │   └── 0002-….md
│   └── agents/             ← this file and its neighbours
├── aimc/                   ← all of our own code, in stacked domains
│   ├── workspace.py  audio/  provenance/
│   ├── analysis/  mastering/  references/
│   ├── generation/         ← command/ then render/
│   └── studio/             ← library/ then the routes
├── song  studio  analyse  master  grab  blend-refs   ← one-line wrappers
├── presets/  lyrics/  refs/  songs/
└── engine/                 ← upstream ACE-Step clone, out of scope
```

`engine/` is a vendored clone of upstream ACE-Step 1.5. Its documentation
describes *that* project's domain, not this one — don't mine it for this repo's
vocabulary, and don't write ADRs about decisions that are really upstream's.

## Use the glossary's vocabulary

When your output names a domain concept (in an issue title, a refactor proposal, a hypothesis, a test name), use the term as defined in `CONTEXT.md`. Don't drift to synonyms the glossary explicitly avoids.

If the concept you need isn't in the glossary yet, that's a signal — either you're inventing language the project doesn't use (reconsider) or there's a real gap (note it for `/grill-with-docs`).

The project's prose — README, guide, documentation, issue notes, docstrings,
comments and user-facing strings — is written in **English**, and its domain
terms are English. Write your own output in English too.

The one exception is the creative content: `lyrics/` holds French song lyrics and
`presets/` holds French generation prompts. Quote those verbatim; never translate
them, because the language is what the model sings.

## Flag ADR conflicts

If your output contradicts an existing ADR, surface it explicitly rather than silently overriding:

> _Contradicts ADR-0007 (event-sourced orders) — but worth reopening because…_
