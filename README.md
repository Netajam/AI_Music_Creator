# AI Music Creator

AI song generation, **100% local**, on a MacBook M2 Pro (16 GB).

Engine: [**ACE-Step 1.5**](https://github.com/ace-step/ACE-Step-1.5) (MIT), cloned into [engine/](engine/).
It is currently the best open music generation model that fits on this machine:
it sings French lyrics, accepts a reference track to imitate a style, and runs
natively on Apple Silicon (MLX for the language model, Metal/MPS for diffusion).

---

## Installation

Already done. For reference, or to reinstall elsewhere:

```bash
git clone https://github.com/ace-step/ACE-Step-1.5.git engine
cd engine && uv sync                 # dependencies (~1.2 GB)
uv run acestep-download              # main models
uv run acestep-download --skip-main --model acestep-5Hz-lm-0.6B
```

The weights (~11 GB) live in `engine/checkpoints/` and are not versioned.

---

## Two ways to use it

### 1. The web interface — for exploring

```bash
./ui
```

Then <http://127.0.0.1:7860>. Handy for trial and error: you hear the result,
adjust the prompt, run it again. That is also where the editing features live
(touch up a passage, separate stems, extend a track).

### 2. The command line — for reproducing

```bash
./song --preset presets/chanson-melancolique.json
```

A JSON preset + a lyrics file = a reproducible, versionable result that can be
re-run identically with `--seed`.

---

## The three generation modes

**Text → music.** A written style, French lyrics:

```bash
./song --style "Chanson française mélancolique, guitare acoustique, voix masculine grave" \
       --lyrics lyrics/exemple.txt \
       --bpm 82 --key "D minor" --duration 180
```

**Reference style** — *a new song that sounds like this one.* This is the "same
style" option: the given track steers the sonic colour, but the lyrics and the
melody stay yours.

```bash
./song --preset presets/chanson-melancolique.json \
       --reference ~/Music/a-track-i-like.mp3 \
       --style-strength 0.25
```

`--style-strength` sets the dial: **≈ 0.2** to take only the mood (recommended),
higher to stick closely to the reference.

**Cover** — *play this track differently.* Here you start from the source audio
itself:

```bash
./song --cover ~/Music/track.mp3 \
       --style "version jazz piano-voix, tempo lent" \
       --lyrics lyrics/exemple.txt \
       --style-strength 0.7
```

---

## Writing the lyrics

A UTF-8 text file, with structure tags in square brackets. **The tags are
written in English, the lyrics in French** — that is the convention the model was
trained on (see its own French example,
`engine/examples/text2music/example_193.json`).

```
[Intro]

[Verse 1]
Les néons pleurent sur le bitume
Je compte les heures qui s'en vont

[Chorus]
Reviens, reviens dans la lumière

[Bridge]
...

[Outro]
```

Common tags: `[Intro]`, `[Verse 1]`, `[Pre-Chorus]`, `[Chorus]`, `[Bridge]`,
`[Outro]`.

For electronic music: `[Build]`, `[Drop]`, `[Breakdown]`, `[Final Drop]`,
`[Hook]`, `[Instrumental Break]`. A section left empty becomes an instrumental
passage. Maximum ~4096 characters.

### Making the bass drop in the right place

The model places the breaks according to the tags, not the words. To make a big
bass land on a specific line, you have to **isolate that line in its own
`[Drop]` section**, preceded by a `[Build]`:

```
[Build]
la ligne qui monte en tension
et celle qui la suit

[Drop]
LA PHRASE QUI DOIT ENCAISSER LA BASSE
```

The `[Build]` triggers the filtered rise, the `[Drop]` releases it. Adding an
empty `[Breakdown]` after the first drop lets the track breathe before it picks
up again, and `[Final Drop]` marks the climax. See
[presets/electro-house.json](presets/electro-house.json) and
[lyrics/exemple-drop.txt](lyrics/exemple-drop.txt) for a complete example, or
[lyrics/exemple.txt](lyrics/exemple.txt) for a classic song structure.

### Describe the style, not the artist

The model's style vocabulary (178,571 entries,
`engine/acestep/genres_vocab.txt`) contains **no artist names**. Writing "in the
style of X" is therefore useless: the model has no representation of X. You have
to describe the sound — `French chanson, electro-pop`, `French House`, `big room
house` are, by contrast, real entries in the vocabulary.

```bash
grep -i "your style" engine/acestep/genres_vocab.txt | head
```

`--language fr` is the default; the model handles 50 languages, and `fr` appears
explicitly in its list.

---

## The levers, from strongest to weakest

### 1. The style description — by far the most important

The whole character of the track comes from here. The model's vocabulary is made
of genre, instrument and production descriptors. Look your terms up in it rather
than inventing them:

```bash
grep -i "techno" engine/acestep/genres_vocab.txt | head -20
```

A good description stacks four layers: **genre**, **instruments**, **vocals**,
**production**. For example:

> `French House` + `basse sidechainée, nappes analogiques` + `voix masculine
> parlée-chantée` + `mix large, sub profond, énergie festival`

### 2. The lyrics structure

The tags decide the arrangement — see "Making the bass drop in the right place"
above. Lengthening a `[Build]`, inserting an empty `[Breakdown]`, doubling a
`[Drop]`: that is what changes the shape of the track.

### 3. Touch up rather than redo

Two tools, far more effective than re-rolling random seeds.

**Vary a take you like** — you keep the track, you move it a little:

```bash
./song --preset presets/electro-house.json --retake-seed 1 --retake-variance 0.15
```

`0.1-0.2` = the same track, slightly different. `0.5+` = a reinterpretation.

**Regenerate a single section** — the rest of the track is preserved:

```bash
./song --preset presets/electro-house.json \
       --repaint songs/ma-prise-seed1.wav --repaint-from 78 --repaint-to 92 \
       --repaint-mode balanced
```

Ideal when a single passage is off. `--repaint-to -1` goes to the end.

### 4. Steering the language model

It is the LM that invents the structure and the arrangement (the "audio codes").

| Option | Default | Effect |
|---|---|---|
| `--lm-temperature` | 0.85 | creativity of the arrangement. 1.1+ = more surprising, less stable |
| `--lm-cfg` | 2.0 | **this is what makes it follow the prompt** (see the warning below) |
| `--lm-top-p` | 0.9 | sampling diversity |
| `--negative` | — | what you do not want to hear |

### 5. The diffusion solver

| Option | Default | Effect |
|---|---|---|
| `--steps` | 8 | more steps = cleaner, but **expensive here** (~36 s/step) |
| `--sampler heun` | euler | 2nd order, cleaner, ~2× slower |
| `--infer-method sde` | ode | stochastic: more variety between takes |
| `--shift` | 1.0 | >1 favours the overall structure, <1 the details |

### 6. The finishing touches

`--fade-in`, `--fade-out`, `--normalize-db -3.0`, `--no-normalize`.

---

## What does nothing on the turbo model

Three traps, because the model ignores them **silently**:

- **Diffusion CFG.** Turbo forces `guidance_scale` to 1.0 at startup ("turbo does
  not use CFG"). To make it follow the prompt, `--lm-cfg` is the one to touch.
- **ADG** (Adaptive Dual Guidance): `base` model only.
- **The `extract` (stem separation), `lego` (multi-track) and `complete` tasks**:
  `base` model only. Turbo can only do `text2music`, `repaint` and `cover`.

---

## Style references: grabbing and blending tracks

### Download a track

```bash
./grab "https://music.youtube.com/watch?v=XXXX"
./grab "artist - title"           # search, takes the first result
./grab "artist - title" --list    # shows the results, downloads nothing
./grab URL --format wav           # lossless, a better reference
```

The files land in `refs/downloads/` (not versioned). Requires `yt-dlp` and
`ffmpeg` (`brew install yt-dlp ffmpeg`).

If YouTube asks for an anti-bot check, go through the browser cookies:
`yt-dlp --cookies-from-browser safari …`.

Downloading from YouTube goes against its terms of service, and the tracks stay
copyrighted unless they are yours, in the public domain, or under a free
licence. Personal use.

### Blend up to three tracks into a single reference

`--reference` takes only one file — but the engine reads only **three 10 s
excerpts** from it (`process_reference_audio`,
`engine/acestep/core/generation/handler/io_audio.py`). When the file is exactly
30 s long, that slicing becomes deterministic: [0-10 s], [10-20 s], [20-30 s].

Hence the trick: fill those three slots with three different tracks.

```bash
./blend-refs a.mp3=45 b.mp3=30 c.mp3=12 -o refs/melange.wav
./song --preset presets/electro-house.json --reference refs/melange.wav --style-strength 0.25
```

The number after `=` is where to take the 10 s from: **aim for a chorus or a
drop, not an intro**. With two tracks, the slots are filled A, B, A.

### The full chain

```bash
./grab "artist - title"
./blend-refs refs/downloads/title.mp3=45 -o refs/melange.wav
./song --preset presets/electro-house.json --reference refs/melange.wav
```

### The same chain, without leaving the studio

The **Inspirations** panel does all of it in one place: paste a URL, and the
track is downloaded, analysed and drawn like a take — sections, tempo, band
lanes, drops, and the stems if you ask for them.

What the panel adds is the step the command line has no place for. On the graph
you scrub to a moment and **keep** it: the studio freezes what it measures there
(the section, the tempo, the band balance, each stem's share) and you write down
what you hear — *"round sub bass, one dry male lead"*. Ticking up to three of
them builds the 30 s reference through `./blend-refs`, selects it in the
composer, fills the BPM when one was really measured, and adds your words to the
style box.

You can keep a **passage** as well as an instant: click a row in the structure
table and the same measurements are read over the whole section — the bands
averaged end to end, every section the passage crosses listed, one tempo only if
it really has one, `tempo varies` if it does not. That is the honest answer to
*"what is this drop like"*, which the one second under the playhead was never
going to give. What a passage hands to a reference is unchanged: ten seconds
from where it starts, because ten seconds is all the engine reads.

Kept moments live in `refs/picks/<track>.json`, and **that folder is versioned**
where `refs/downloads/` is not. The audio can be fetched again in a minute; the
listening cannot. Deleting the downloads loses nothing that matters.

> The style box is sent as `--style`, which **replaces** the preset's style
> rather than extending it. So the studio seeds the box with the preset's own
> text before adding your words — leaving it empty keeps the preset untouched.

---

## The rhythm of the voice

There is **no** direct control over syllable placement: `get_lyric_timestamp`
analyses the *produced* audio (through cross-attention) to extract an LRC from it
— that is an output, not an input. No time tag is read from the lyrics.

What actually affects the delivery:

| Lever | Effect |
|---|---|
| **Line breaks** | the strongest. A short line is hammered out, a long line is crammed in |
| **Syllables / duration density** | little text in a long section = the model stretches it out and stumbles |
| **`--bpm`** | the grid everything locks onto |
| **The prompt** | `spoken word`, `staccato`, `rapid-fire delivery`, `half-time` really do shift the phrasing |

---

## Publishing: lossless, and nothing else

Distributors require **lossless** (WAV or FLAC, 16 or 24 bit, 44.1 kHz minimum).
That is why `--format` defaults to **`wav`**: a take is born lossless or it never
will be. **An MP3 cannot be repaired** — converting to WAV does not invent back
the information thrown away at encoding time.

`mp3`, `opus` and `aac` are still available, but they are **listening** formats:
`./master` refuses them, and the studio shows them as "listening only, not
publishable".

### Listening without losing the take

Do not audition in MP3 and then regenerate in WAV — that is a different take.
Generate the WAV, and derive an MP3 from it to listen. The take stays rigorously
the same.

```bash
./song --preset presets/electro-house.json --seed 1          # wav, by default
ffmpeg -i songs/the-track.wav -b:a 320k songs/preview.mp3  # to listen
```

A 145 s WAV weighs about 28 MB (42 MB once mastered in 24 bit) — nothing next to
the 11 GB of models already on the disk.

### Mastering

From the studio: select the take, set LUFS / peak / silences / bit depth in
**Publish**, click **Master**. The log is shown live and the before/after
measurements are presented under the button.

From the command line:

```bash
./master songs/the-track.wav
./master songs/the-track.wav --lufs -16 --head 2 --tail 3   # Apple Music target
./master songs/the-track.wav --flac --bits 16 --sample-rate 44100
```

The script measures, normalises in two passes, adds silence at the head and the
tail, and reports an abruptly cut ending. It **refuses** a compressed source
(`--force` to override).

### Two traps in `ffmpeg -af loudnorm`

The script works around them, but if you write the command by hand:

- **The output comes out at 192 kHz.** The filter works internally at that rate
  and does not return to the original one. Without `-ar 48000`, the master comes
  out at 192 kHz.
- **`linear=true` in a single pass does nothing.** Linear mode needs the measured
  values; without them it falls back to dynamic compression. You have to measure
  (`print_format=json`), then feed back `measured_I`, `measured_TP`,
  `measured_LRA`, `measured_thresh` and `offset`.

### Loudness targets

| Platform | Integrated | True peak |
|---|---|---|
| Spotify, YouTube, Amazon | -14 LUFS | -1 dBTP |
| Apple Music | -16 LUFS | -1 dBTP |

The two takes produced so far landed at -15.1 and -14.9 LUFS: the model comes out
naturally in the right range, no brutal limiter is needed.

---

## The identity of a take

Every take comes with a `<track>.json` written by `./song`. It holds the
settings, plus two fields that answer questions the settings alone do not settle:

- **`fingerprint`** — a fingerprint of the **decoded** audio content. Two files
  with the same fingerprint contain the same take, whatever their container or
  bit depth; two files with the same name and different fingerprints are two
  unrelated takes. The studio shows it under each take and **warns in plain
  words** when two files sharing a stem do not contain the same take — exactly the
  `ma-prise-seed1.mp3` / `ma-prise-seed1.wav` trap.
- **`code`** — a fingerprint of our own modules used for the render, plus the
  revision of `engine/`. Without it, "what it takes to remake this exact take" is
  a false promise as soon as generation changes. The studio compares it against
  the code that is present and warns when they differ.

A take with no manifest (an older one, or one recovered from elsewhere) can be
given one from the studio, under **Settings for this take → Reconstruct
settings**. It is then marked `"provenance": "reconstructed"`, written to
`<full filename>.json` so it is never confused with a namesake's, and displayed
as reconstructed: the seed in it is a guess read from the filename, and the
original code stays unknown.

---

## Presets

A preset bundles style, lyrics, tempo and key. The paths it contains are relative
to the preset itself.

```json
{
  "style": "Chanson française mélancolique, guitare acoustique et piano feutré…",
  "lyrics": "../lyrics/exemple.txt",
  "language": "fr",
  "bpm": 82,
  "key": "D minor",
  "duration": 180
}
```

A preset no longer pins the output format: with no `format` key, it renders
lossless. `--format` is what decides, and its default is `wav`.

Four are provided: [chanson-melancolique](presets/chanson-melancolique.json),
[electropop](presets/electropop.json), [rap-jazz](presets/rap-jazz.json) and
[electro-house](presets/electro-house.json) (with drops on the chorus). They are
examples, and the workspace they belong to is this repo itself — see
[colab/README.md](colab/README.md) on keeping your own somewhere else.

Any option passed on the command line **overrides** the preset:

```bash
./song --preset presets/electropop.json --bpm 128 --duration 200
```

The settings that worked for a given style, and the mistakes they cost, are
recorded in the [recipe book](docs/recipes.md).

---

## Memory: what you need to know

On a Mac, the diffusion side runs in **float32** (MPS does not do bfloat16 here).
The 2B DiT therefore takes ~8 GB, on top of which come the language model and the
embeddings — **~11 GB in total out of your 16 GB**.

In practice: **close the big applications before starting a generation** (a
browser with many tabs, Docker, virtual machines, heavy editors). Otherwise macOS
starts swapping and generation becomes very slow.

The default configuration is already the leanest one:

| Setting | Value | Why |
|---|---|---|
| DiT | `acestep-v15-turbo` (2B) | the 4B XL does not fit in 16 GB |
| LM | `acestep-5Hz-lm-0.6B` | the 1.7B costs ~3.5 GB more |
| `--count` | 1 | each extra variant doubles the memory peak |
| `--steps` | 8 | the value intended for the turbo model |
| DiT MLX | disabled | the MLX conversion ALSO keeps the PyTorch copy in memory (~9.5 GB each): that is what was crashing the 16 GB |

If it still struggles:

```bash
./song --preset presets/chanson-melancolique.json --offload   # offloads to the CPU, slower
./song --preset presets/chanson-melancolique.json --no-lm     # no LM, ~1.5 GB less
```

Expect a few minutes for a 3-minute track.

Two analyses load a model of their own, and neither can share the machine with a
generation — the studio refuses to start them while one is running, and refuses
to run them at the same time as each other:

| Pass | Model | Peak | Cost |
|---|---|---|---|
| `./analyse --align` | MMS_FA, 1.2 GB | ~3 GB | about a minute |
| `./analyse --stems` | Demucs, 320 MB | 2.3 GB | about a third of the track's length |
| `./analyse --tags` | the above, plus AST, 350 MB | 2.7 GB | roughly twice `--stems` |

`--tags` is `--stems` with a name attached to what it finds: it rides inside the
same pass and asks an AudioSet tagger which instrument *families* are playing in
`other`, and which genre the mix sounds like. It reports families rather than
instruments, and often reports nothing — see `aimc/analysis/tags.py`, where what
it can and cannot hear is measured rather than claimed.

Both run as a subprocess rather than inside the studio, so torch goes back to
the system when they finish instead of being held until the tab is closed.

---

## When 16 GB is the thing in the way

Everything above is shaped by the ceiling: the 2B DiT rather than the 4B, the
0.6B LM rather than the 1.7B, one take at a time, and `night/runner.sh` reloading
both checkpoints for every single take because holding them across takes drove
the machine into swap.

For a long batch, that ceiling can be rented away for an afternoon.
[`colab/AI_Music_Creator.ipynb`](colab/AI_Music_Creator.ipynb) runs this repo on
a Colab GPU: same presets, same lyrics, same render path, same manifest beside
each take. What changes is that `night/batch_render.py` — the load-once worker
that lost here — becomes the one that runs, and a take costs seconds rather than
nine minutes.

It is not free: about ten minutes of installing the engine and downloading the
weights, paid again every time Colab hands out a new machine. A seventy-five
take queue earns that back many times over; one experimental take does not, and
for that the Mac is still the shorter path. See [`colab/README.md`](colab/README.md).

---

## Checking without loading anything

`--dry-run` validates the parameters and shows what would be generated, without
touching the models or the memory:

```bash
./song --preset presets/chanson-melancolique.json --dry-run
```

---

## Code quality

```bash
./check          # linter (ruff) + type checking (mypy)
./check --fix    # first fixes what ruff knows how to fix
```

Both run on the seven modules of our own only; `engine/` is an upstream clone and
is not checked.

Typing is at "moderate" strictness: every function must be annotated, and bare
`dict` or `list` are refused — a `dict[str, Any]` at least says that the keys are
strings. We do not turn on full `--strict`, which would forbid those explicit
`Any`s: the JSON payloads of the studio and the manifests really are
heterogeneous, and claiming otherwise would be a lie.

mypy reads the types of the dependencies (numpy, fastapi, pydantic) from
`engine/.venv` — hence the warning from `./check` if the engine is not installed
yet. Without it, the check would come out green without checking anything.

---

## Structure

The commands are one-line wrappers; all of our own code lives in the `aimc/`
package, stacked bottom to top — each domain only knows about those below it.

```
song                 generates a song            -> aimc.generation.cli
studio               the repo's web interface    -> aimc.studio.server
analyse              analyses a track            -> aimc.analysis.cli
master               prepares a master           -> aimc.mastering.cli
grab                 downloads a track           -> aimc.references.grab
blend-refs           builds a reference          -> aimc.references.blend
ui                   wrapper for the upstream Gradio interface
check                linter + type checking (ruff, mypy)

aimc/
├── workspace.py     where the repo's files live, and unique_path
├── audio/           the ffmpeg toolbox — no numpy, no model
├── provenance/      the identity of a take: fingerprint, manifest, code version
├── analysis/        sections, tempo, voice, drops (signal processing),
│                   plus two model passes: lyric alignment and stem separation
├── mastering/       distribution targets, EBU R128 measurement, normalisation
├── references/      grab + blend + picks: building a style reference
├── generation/      command/ (the command line) then render/ (the engine)
└── studio/          library/ (what we know about takes) then the routes

refs/downloads/      downloaded tracks (not versioned)
presets/             song configurations (JSON)
lyrics/              lyrics in French (UTF-8)
songs/               generated tracks (not versioned)
engine/              upstream ACE-Step 1.5 + .env tuned for 16 GB
engine/checkpoints/  model weights, ~11 GB (not versioned)
pyproject.toml       ruff and mypy settings (not an installable package)
```

Three rules hold this stack together, and `./check` verifies them — a domain only
imports from lower-ranked domains, plus:

- **`acestep` is only imported inside `aimc/generation/render/`**, and always
  inside a function: the engine is only loaded once the arguments have been
  validated. That is what keeps `--help` and a rejected argument instant, without
  reserving memory.
- **`audio/`, `mastering/` and `references/` do not import numpy**: `./master`,
  `./grab` and `./blend-refs` run under the system python3, without
  `engine/.venv`.

All the options: `./song --help`.
