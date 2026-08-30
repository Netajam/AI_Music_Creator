# The recipe book

What each style needs, and the mistakes we have already paid for.

The README explains **which levers exist**; this book records **which values
worked**, on which song, and what we heard when they didn't. A recipe is only
worth having if someone listened to it, so every card states its confidence.


> The presets, lyrics and takes named below are **not in this repository**. They
> belong to the workspace — the private half of the tree, see
> [`colab/README.md`](../colab/README.md) — and are named here because what a
> rule cost, and on which take, is the part worth keeping. The rules themselves
> need none of those files.

---

## The loop

A song is cooked in this order. Skipping a step costs a take, and a take costs
seven minutes.

1. **Gather the references.** `./grab "URL"`, or `./grab "artist - title" --list`.
2. **Analyse them.** `./analyse refs/downloads/X.wav` — tempo, sections, drops.
3. **Build the reference.** `./blend-refs` — 30 s, one single tempo grid.

   Steps 1 to 3 are also the studio's **Inspirations** panel, in one place and
   with the graph in front of you. Its advantage is not the clicking: it is that
   what you keep is written down — the second or the passage, what was measured
   there, and what you heard in it — in `refs/picks/`, which is versioned.
   Offsets chosen by eye in a terminal are the part of this loop nothing has
   ever recorded, and re-deriving them a week later is guesswork.

   Click a section rather than the graph to read a whole passage: bands averaged
   over its length, and `tempo varies` instead of a number when it holds more
   than one. A passage that changes tempo is the one you do not cut a reference
   from — step 3 wants a single tempo grid.

4. **Write the lyrics** at the density you're aiming for (below).
5. **Write the preset**, then `./song --preset ... --dry-run`.
6. **Generate one seed.** One.
7. **Re-analyse the take**, then **listen**.
8. **Change one lever at a time.** Two changes at once and you no longer know
   which one did the work.

---

## Lyric density

The most underrated lever. Too much text and the model recites without
breathing; too little and it invents a structure of its own.

| Take | Characters / 200 s | What we heard |
|---|---|---|
| `all-dayggering` v1 | 3362 (17 chars/s) | recitation, flat, no variation for 140 s |
| `all-dayggering` v2 | 1845 (9 chars/s) | all over the place, impossible to dance to |
| `all-dayggering` v3 | 2009 (10 chars/s) | *not yet heard* |
| `all-in-tonight` v1 | 1164 over 180 s (6.5 chars/s) | too gentle — but the reference was the fault, not the density |
| `all-in-tonight` v3 | 1115 over 145 s (7.7 chars/s) | "pretty good", and still "the vocals are too apparent" |
| `all-in-tonight` v4 | 707 over 145 s (4.9 chars/s) | *never rendered* — three sections left empty on purpose |
| `omad` v4 | 1412 over 175 s (8.1 chars/s) | the take that was liked; sung-spoken, not rapped |

**Rule of thumb**: around **10 characters per second** for a fast flow (deejay,
rap), lower for sustained singing. But density alone doesn't settle it — v2 sat
at a good density and still failed, because its lines were shouted fragments
instead of whole bars. What matters is **one line per bar, a whole line**.

---

## The traps

Each of these cost us a take. All observed, none assumed.

### Mixing two tempos in the reference

A 30 s blend holding both 170 BPM and 131 BPM material: the take speeds up and
slows down for no reason. **One reference, one grid.** `./blend-refs` accepts the
same file several times at different offsets, which gives you three moments of
one track without ever changing tempo:

```bash
./blend-refs refs/downloads/X.wav=50 refs/downloads/X.wav=115 refs/downloads/X.wav=150 -o refs/style.wav
```

### Inventing bracketed cues

`[strings alone, no drums]`, `[sirens, break rolling in]` — the model does not
read these as stage directions, it treats them as **sections in their own
right**. The drums vanish, the voice is left alone, and the song sounds like it
stopped. **Known tags only**: `[Intro]`, `[Verse]`, `[Chorus]`, `[Build]`,
`[Drop]`, `[Breakdown]`, `[Bridge]`, `[Outro]`.

### Too many sections, or too few

Counted on `all-dayggering`:

| Sections in the lyrics | Sections `./analyse` heard back | Verdict |
|---|---|---|
| 5 | 5, a single drop at 162 s | flat, nothing ever lifts |
| 18 | 9, five drops, bass energy 0.12 → 0.58 | all over the place |
| 8 | *not yet heard* | — |

**Around 8 sections** for three minutes, and let them be long.

### A chorus that isn't identical

A chorus reworded on each pass never sticks. **Copy and paste it word for word**
every time — that is what makes a song memorable, not variety.

### Setting `--lm-cfg` by guesswork

It decides how literally the tags are followed. Observed:

| Value | Effect |
|---|---|
| 2.0 (default) | tags ignored, arrangement stays flat |
| 2.5 | tags followed **to the letter**, the arrangement restarts every few seconds |
| 1.8 | *not yet heard* |

Raising CFG to fix a flat song works — and overshoots fast.

### `--count 2` takes the machine down

The takes go into a single MPS graph: at 200 s that is `MPS backend out of
memory` (12.75 GiB + 6.82 GiB against a 20.13 GiB ceiling). **Nothing is
written.** For several takes, run one invocation per seed, back to back.

### `./song` exits 0 even when it failed

The OOM above ends in `exit 0`. **Read the tail of the log** and look for
`Done` / `Terminé`; never trust the exit code, least of all in a script or a
background task.

### A style description over 512 characters

`--style` is rejected past that, and the message only arrives after the preset
has loaded. `--dry-run` tells you in two seconds.

Worse in the background: launched under `nohup`, that rejection lands in the log
within a second and the shell reports nothing. A take was announced as rendering
on the strength of the launch alone, and the next round of listening was spent
on the **previous** take — the one the new preset was meant to replace. Confirm
a background run is alive (`pgrep -f aimc.generation.cli`, or the log's first
lines) **before** saying it started, and never describe a take that only a
process ID vouches for.

### YouTube "Topic" links

`music.youtube.com` often points at a `- Topic` channel that `yt-dlp` refuses
("Video unavailable") even though the video exists. The `si=` parameter on a
share link changes nothing. `./grab "artist - title" --list` finds the same
recording on another upload.

### Holding the models in memory across takes

Loading the DiT and the 5Hz LM costs about three and a half minutes, and every
take pays it again because every take is a new process. Over a hundred songs
that is five and a half hours of loading the same two checkpoints. The obvious
fix — one process, models loaded once, a loop over the queue — was built and
measured.

**It does not work on 16 GiB.** The first take rendered fine and fast, 445 s for
a 185 s track against 617 s for a comparable take through `./song`. The next one
hung. Not failed: hung. Swap sat at **15.5 GiB of 16**, the process stayed alive
at 9 % CPU with an RSS of 53 MB, and the log stopped at

    [DCW] Built DWT1D for wavelet='haar'

for fifty minutes without an error, a traceback, or a line of output. Killing it
brought wired memory down from 6.2 GiB to 3.8 GiB and swap back to 4.7 GiB
within a minute.

That is the same silent shape as the `--sampler heun` trap below, and it is
worth reading the two together: on this machine, **a diffusion that goes quiet
right after `Built DWT1D` has run out of memory**, whatever else it looks like.
Paying the loading time per take is what buys the machine back.

**Measured again on a second night**, this time as a clean A/B over one ledger,
split by which script wrote each row:

| Path | Takes | Mean per take |
|---|---|---|
| a fresh process per take | 55 | **9.0 min** |
| models held across takes | 6 | **34.4 min** |

Not a hang this time — every take completed — just four times slower, with one
175 s bossa nova taking 41 minutes. `vm_stat` reported 96 million swapouts and
67 MB unused physical memory while it ran. The failure mode varies; the verdict
does not.

**Pay the 3.5 minutes. One process, one take.**


### `--mlx-dit` loads both backends at once

Worth trying — an MLX-native DiT on Apple Silicon is exactly the right idea — and
it dies before the first step:

    MLX diffusion failed (MPS backend out of memory (MPS allocated: 11.76 GiB,
    other allocations: 8.95 GiB, max allowed: 20.13 GiB)); falling back to PyTorch

then the fallback dies too, on a 375 KiB allocation. The MLX weights do not
*replace* the PyTorch ones, they are added to them. Measured on a 60 s
instrumental, which is as small as a test gets, so nothing shorter will save it.

This one at least is loud: it ends in `exit 1` with a traceback, unlike almost
every other memory failure in this book.

### Mistaking `./analyse` for ears

The tool counts sections and bass energy; it has no idea whether any of it
sounds good. Use it to **confirm an impression** — "all over the place" shows up
in the section count — never to decide in place of listening.

### Reading the band lanes as levels

The two lanes under the bars — mids 150 Hz–2 kHz, highs 2–8 kHz — are each
shaded against **their own** loudest second, not against each other. A dark mid
lane and a pale high lane does not mean there is more mid than high in the mix;
it means the mids are near their peak here and the highs are not. They answer
"when does this band carry the track", which is the question the bass bars
already answer for the bottom end, and nothing else.

Two more limits worth knowing. The profile decodes at 16 kHz, so the top lane
stops at 8 kHz: a track's actual air is above what it can see. And the lane is
smoothed over three seconds — a one-second FFT catches the beat wherever it
falls, and unsmoothed the lanes came out as dither.

### Asking the bands which instrument is playing

They cannot say. A kick and a bass line are both under 150 Hz; a hi-hat and a
cymbal are both in the top lane. What names families is **`./analyse --stems`**,
which separates the mix with Demucs into drums, bass, vocals and other — and
even that stops at four: `other` is every harmonic instrument that is neither
the bass nor the voice, guitars and keys and pads together, and Demucs cannot
tell them apart.

**`./analyse --tags`** goes one step further and asks an AudioSet tagger what is
in that stem. One step, not the whole way: it answers with *families* — keyboard,
plucked string, bowed string — because no single label it returned over four
measured tracks ever reached 0.19, and what is readable is several labels
agreeing rather than any one score. On a reggae take it says `keyboard`; on a
ragga jungle it says nothing at all, because once the drums, bass and voice come
out of a breakbeat track there is nothing left in `other` but bleed. That
silence is the correct answer, not a failure. It also reads the genre off the
mix, which needs no separation and is the more reliable half — but only on
music the tagger knows: real jungle scored 0.050 on `Drum and bass`.

It costs about a third of the track's length and 2.3 GB, so nothing triggers it
on its own — the studio has a button, and refuses while a generation or an
alignment is running.

Read an **absent** verdict as the solid one. It was calibrated by filtering a
family out of a real take: with the bass high-passed away, the bass stem came
back at exactly 0.000 for 90 seconds. A **present** verdict is the weaker claim
— a stem for an instrument that genuinely is not there still fills up with bleed
from the three that are.

### Fixing a voice with the negative prompt alone

`falsetto` and `female lead vocals` were both in the negative of
`all-in-tonight` v2, and the take still came back with a high, thin voice.
Moving the same requirement into the **positive** description — `one deep male
baritone voice in a low chest register, dry and gravelly` — fixed it in one
take, with every numeric setting held identical (verified from the two
manifests: same bpm, key, strength, `lm_cfg`, sampler, steps and seed). The
negative narrows; only the description **decides**. This holds for anything the
model has to *produce* rather than avoid: register, timbre, how many voices.

### Asking for the clutter, then blaming the model

v2's description ordered `heavy distorted sub bass riff driving every bar`,
`busy hi-hats` and `bright stabs`. What came back was a repetitive bass and a
pile-up before every drop — which is what was written down. `riff` asks for one
repeated figure, `busy` asks for business. Read the description back as if it
were the complaint before blaming the take: `a melodic bassline that moves and
changes through every bar` and `sparse uncluttered arrangement with only a few
elements at a time` produced the opposite from the same seed.

### `[Build]` is an order to stack risers

The tag is legal and it works — that is the problem. Removing both `[Build]`
sections from `all-in-tonight` (7 written sections down to 5) took the take from
8 heard sections and five drops to **3 sections and one continuous 89 s
stretch**. If a style is meant to be relentless rather than event-driven, leave
the tag out: the reference for that take holds two sections across its whole
length. The cost is paid at the start — the same edit dropped the first 51 s to
bass 0.24 and pushed the first drop from 13 s out to 55 s.

### `heun` and `sde` cancel each other out

`--sampler heun --infer-method sde` is accepted without complaint, and then the
engine prints, in the middle of a 180-line log:

    Heun sampler is not compatible with SDE; falling back to Euler.

The run continues and produces a take with a sampler you did not choose.
`--dry-run` shows neither setting, so it cannot warn you. Anything set for a
reason has to be **checked in the log**.

### `--sampler heun` never finished a run here

Twice, on a 145 s take: the log reaches `[DCW] Built DWT1D`, diffusion starts,
and the process dies seconds later. No traceback, nothing matching `error` in
184 lines, no audio, and an empty `.run-*` directory left behind. The second
attempt ran under `nohup`, so it was not the session going away.

**Cause not confirmed.** The shape matches the silent MPS out-of-memory
documented above, and a second-order sampler evaluates the model twice per step,
which is the right kind of extra pressure — but nobody has verified it. Until
someone does, treat heun as unavailable on this machine and leave the sampler at
euler.

### Judging a reference by its genre instead of its stems

`all-in-tonight` v1 took its style from a track of the right genre, at a
plausible tempo, that had already been picked in the studio. `./analyse --stems`
on it: **vocals 6% of the mix, peak 0.31**, against 17% and 0.88 for the track
that eventually worked. A lyric written to be shouted, aimed at a record whose
voice is a background texture, came back — heard, not measured — as *"too
gentle, the singer sounds like a lover"*.

Run `--stems` on a candidate reference **before** writing the preset. The vocal
share says whether the record has a singer or an atmosphere, and no amount of
prompt will put a lead where the reference has none.

### Blaming the reference without checking the windows you cut

When v2 came back too high-pitched, the obvious culprit was the reference: a
track with a prominent female lead. It was wrong. The three 10 s windows
actually cut carried vocals at **0.093 to 0.118**, below that track's own mean
of 0.169 and nowhere near its 0.876 peak. The loud part of a record is not
necessarily the part you took, and a reference is 30 s, not a song. Check the
stems **of the windows**, not of the track.

### There is no key detector

Every preset's `key` is written by hand and nothing in this repository measures
it — D1 of the inspiration ticket says so in as many words. A chromagram folded
from `aimc.analysis.spectral` and correlated against the Krumhansl-Schmuckler
profiles is a usable hint, but read its **spread** before trusting it:

| Track | Top candidates | Verdict |
|---|---|---|
| `Talk_of_the_Town.wav` | A major +0.450, A minor +0.416 | no answer: every pitch class between 0.07 and 0.10 |
| `Prada.wav` | F major +0.667, C major +0.526 | usable: a chroma with real structure |

A flat chroma means the track has **no harmony to read**, not that its key is
hard — and it agrees with the stems, which put that first track's harmonic
content at 9.5% of the mix. Say which of the two you have when you write the
`key` into a preset.


---

## The cards

### Jungle / drum and bass toasting — `all-dayggering`

*Confidence: in progress. v1 and v2 heard and rejected, v3 not yet heard.*

| Setting | Value | Why |
|---|---|---|
| `bpm` | 172 | jungle is written at 170-175; `./analyse` reports it as 85, the half-time |
| `key` | A# minor | measured off the references |
| `duration` | 200 | drop toward 150 s if the model keeps inventing structure |
| `style_strength` | 0.3 | enough for texture, not enough to impose the grid |
| `lm_cfg` | 1.8 | see the trap above |
| `fade_out` | 4 | without it the song stops dead |

The description has to say **what never stops**: `one continuous rolling amen
break that never stops`, `drums running under every section`. Asking for `long
rising build-ups` gets you EDM risers, not jungle.

The negative prompt does the real work — it names the failures we heard:
`tempo changes, accelerando, abrupt stops, drums dropping out, a cappella
sections, doubled vocals, layered vocal stacks`.

Files: `presets/all-dayggering.json`,
`lyrics/all-dayggering.txt` (the rejected
versions are kept beside it as `-v1` and `-v2`).

### UK bass house club anthem — `all-in-tonight`

*Confidence: in progress. v1 and v2 heard and rejected, v3 heard and called
"pretty good", v4 never rendered.*

| Setting | Value | Why |
|---|---|---|
| `bpm` | 140 | measured off the reference; 128, from the first reference, was heard as "too gentle" |
| `key` | F major | chromagram +0.667 on a chroma with real structure — see the trap |
| `duration` | 145 | close to the reference's 132 s; at 180 s the take wandered for its first minute |
| `style_strength` | 0.55 | carries the reference's weight without imposing its vocal |
| `lm_cfg` | 2.2 | at 2.0 the arrangement stayed flat and the first drop landed at 46 s |
| `sampler` | euler | heun never completed a run here — see the trap |
| `fade_out` | 3 | |

**The reference is three windows of one track**, at 90, 104 and 118 s, each
measured at 140 BPM with `varies: false` and a low band of 0.92-0.93 — the
hardest passage of the record, on one grid. They are written down in
`refs/picks/Prada.wav.json` with what was
measured at each. The 85-99 s passage of the *first* reference was deliberately
left out of that one: 126 BPM against 128 elsewhere, and drumless.

**What the description must say.** Name the voice's register positively (`one
deep male baritone voice in a low chest register, dry and gravelly`), ask for a
bassline that *moves* rather than a `riff`, and ask for space
(`sparse uncluttered arrangement with only a few elements at a time`). Three
traps above were all earned on this song's description.

**What the lyrics must do.** Open on the `[Chorus]` — an `[Intro]` bought 12 s
at bass 0.01 before anything happened. Leave `[Build]` out. Keep the chorus
identical word for word, three times.

**What was still wrong after v3**, in the listener's words: *"the vocals are too
apparent, it could lack of mystery, some glitch in the song, the musicality is
maybe also too conventional."* The untried answer, drafted and never rendered,
is `presets/all-in-tonight-v4.json`: the
lyric cut to 707 characters with `[Intro]`, `[Breakdown]` and `[Outro]` left
**empty** so they become instrumental passages, the voice asked for `buried low
in the mix, drenched in reverb and dub delay`, F minor, `lm_cfg` 1.9,
`lm_temperature` 1.15. It died in the sampler trap, twice, before producing
anything.

Files: `presets/all-in-tonight.json`,
`lyrics/all-in-tonight.txt`. The rejected
versions are kept beside them as `-v1`, `-v2` and `-v3`; **v3 is the one that
was liked**, and it is `all-in-tonight-seed1-20260828-172757.wav`.

### Tropical house with a Latin groove — `omad`

*Confidence: heard and validated — "a banger", on the first take of this preset,
seed 1. One take heard, so the settings are validated as a **bundle**; none of
them has been moved on its own since.*

| Setting | Value | Why |
|---|---|---|
| `bpm` | 100 | reggaeton dembow tempo. 120 and 128 were both tried on this text and neither was kept |
| `key` | A minor | written by hand, not measured — see the trap |
| `duration` | 175 | |
| `style_strength` | 0.45 | groove and production from the reference, nothing of its arrangement |
| `lm_cfg` | 2.2 | |
| `lm_temperature` | 0.7 | 0.6 on the take before this one; both gave a stable pitch |
| `--steps` | 16 | on the command line, not in the preset — the last three takes all used it |
| `fade_out` | 4 | |

**What the description must say — the delivery, in the positive.** This is the
whole card. Four takes were rejected for sounding comic, and the style block was
not what fixed it: `une voix masculine grave, nonchalante et décontractée,
presque murmurée, jamais théâtrale` was. It is the same lesson as *Fixing a voice
with the negative prompt alone*, one register further out — the negative can
forbid `comique`, `cabaret`, `voix qui surjoue`, and did, in the two takes that
still came back comic. **Attitude has to be asked for, not banned.** A text that
is funny on the page needs a performance that plays it straight; asked for
animation, in any genre, it becomes a novelty song.

The rest of the description is ordinary: `groove reggaeton dembow détendu`,
`lead mélodique de marimba et de flûte synthétique`, `congas, shakers`,
`refrain large et accrocheur`, `production moderne, claire et spacieuse`.

**The route to it**, since the style dial was swung about as wide as it goes and
the same complaint followed the song through four of the five stops:

| Take | Style | What was heard |
|---|---|---|
| `omad-chanson-…183746` | orchestral chanson 120, Aznavour reference | "like a paillard song, not classy at all" |
| `omad-chanson-v3-…191051` | piano + violin + cello 92, no reference | "all over the place", the voice changing pitch inside a single word, "between classical and modern" |
| `omad-chanson-v4-…193158` | same, one note per syllable, temp 0.6, 16 steps | still not the target style |
| `omad-electro-…194529` | electro-pop 120, Stromae reference | "too much like a funny song" |
| `omad-tropical-…195943` | **this card** | "a banger" |

The two club-house takes that opened the session
(`omad-seed1-…180331`, `omad-v4-seed1-…182552`) have **no verdict recorded**.

**What this card does not establish.**

- The reference is the **whole 251 s file**, not a 30 s blend on one grid, and
  `--stems` was never run on it. Two traps in this book say to do both. It
  worked anyway, and nobody knows how much the reference contributed.
- `--steps 16` arrived in the same take as three other changes and has never
  been isolated. It may be doing nothing.
- The lyrics were never varied against this preset. The v4 text spells `O-M-A-D`
  out as a chant and ends most lines in an exclamation mark, which is the shape
  of a drinking song on the page; whether the deadpan delivery won *despite*
  that, or whether it stopped mattering once the groove was right, is untested.
- The lyric carries a bracketed cue, `[beat s'arrête, voix seule]`, in the
  outro — exactly what *Inventing bracketed cues* warns against. It survived
  into the take that was liked. Unexplained; do not read it as a licence.

Files: `presets/omad-tropical.json`,
`lyrics/omad-v4.txt` — 1412 characters over 175 s
(8.1 chars/s) in 8 sections, both inside this book's rules of thumb. The
rejected directions are kept beside the preset as `omad.json` (club house),
`omad-chanson.json`, `omad-chanson-v3.json`, `omad-chanson-v4.json` and
`omad-electro.json`; earlier lyric versions as `omad-v2.txt` and `omad-v3.txt`,
with the original untouched draft at `songs/omad.txt`.

### The night-run shape — 100 songs, ten collections

*Confidence: structural only. One take analysed, none heard at the time of
writing. Read every claim below as "the analyser agrees", never as "it sounds
good" — that distinction is the whole point of the trap above.*

A single lyric and preset shape was used for all hundred songs of
[`night/`](../night/README.md), so that what varies between them is the style
and not the scaffolding:

| Element | Value |
|---|---|
| sections | **8**, in the order Intro, Verse, Chorus, Verse, Chorus, Bridge or Breakdown, Chorus, Outro |
| chorus | three passes, **copied and pasted**, never reworded |
| density | 7.5 to 10.5 characters per second — the lower half for sustained singing, the upper for a spoken or scanned delivery |
| lines | one line per bar, whole lines, never shouted fragments |
| `lm_cfg` | 2.2, except 1.9 for the styles meant to be relentless rather than event-driven |
| `duration` | 165–200 s |
| `--steps` | 8, the turbo model's own default |
| `sampler` | euler, always |
| `fade_out` | 4 |

The voice is named **in the positive** in every description — register, timbre,
attitude, `une syllabe par note` — and the negative only ever forbids. Both of
those are the `omad` and `all-in-tonight` cards, applied a hundred times.

**What one measurement says.** `autoroute-du-soleil`, the first take of the run:
requested 118 BPM, measured 117; 8 written sections came back as **11 heard
sections with four drops**, bass energy climbing 0.18 → 0.86, vocals detected
throughout. Set that beside the two failures this book already records for the
same question — 5 written sections heard as 5 with a single drop at 162 s
("flat, nothing ever lifts"), and 18 written heard as 9 with five drops ("all
over the place") — and the eight-section shape lands between them, which is
where it was aimed.

One take is one take. What it establishes is that the shape is not obviously
broken; what it cannot establish is that any of it sounds good.

### The other presets

No card yet: the settings are in the presets, but nobody has written down what
was actually heard.

- **French electro-house** — `presets/techno-pouf3-anthem.json`
- **Roots reggae** — `presets/babylon-reggae.json`
- **Melancholic chanson** — [`presets/chanson-melancolique.json`](../presets/chanson-melancolique.json)

---

## Adding a card

A card is filled in **after listening**, never from the preset alone.

```markdown
### Style — `song-name`

*Confidence: heard and validated | in progress | rejected.*

| Setting | Value | Why |

What the description must say, what the negative must forbid,
and what we heard when it went wrong.
```
