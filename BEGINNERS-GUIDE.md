# Making music with AI — a guide for getting started

This guide is for someone who is **not a developer**, who has never opened a
terminal, and who just wants to make songs.

Good news first: **you need neither Claude Code, nor a Mac, nor any programming
knowledge.** The engine used here, [ACE-Step 1.5](https://github.com/ACE-Step/ACE-Step-1.5),
is free and open source, and there is a version that runs in a plain browser.

---

## Step 0 — Choose your path

Three routes, from the simplest to the most complete. **Start with A.** Only move
on to B if you really want to run everything on your own machine.

| | Route A — Online | Route B — On your machine | Route C — Like this repo |
|---|---|---|---|
| **Installation** | none | download + unzip | terminal required |
| **Hardware** | anything, even a phone | PC with an NVIDIA card, or an Apple Silicon Mac | same as B |
| **Working in** | 2 minutes | 1 to 3 hours (downloads) | half a day |
| **Cost** | nothing | nothing | nothing |
| **Private** | no, it goes through a server | yes, 100% local | yes |
| **Who for** | everyone | you want to generate a lot, with no limits | you want to script and reproduce |

> **The model is exactly the same in all three cases.** The only difference is
> where the computation runs. Do not put yourself through an installation if you
> only want to try it out.

---

# Route A — Without installing anything (recommended to start)

## A.1 — The official site

Go to **<https://acemusic.ai>**.

This is the online service from the team that built the model. They advertise it
as free and requiring no graphics card. You will probably have to create an
account. You type a description, you wait, you listen.

## A.2 — The Hugging Face demo

Another option, with no account: **<https://huggingface.co/spaces/ACE-Step/Ace-Step-v1.5>**

This is the model's public demo. It is free but shared between all visitors:
depending on the traffic, you may end up in a queue.

**Skip straight to the "Writing a good prompt" section below** — that is where
everything is decided, and it applies to all three routes.

---

# Route B — On your machine, with no terminal (or almost)

## B.1 — First: can your machine handle it?

Not everything runs on every machine. Check **before** downloading several tens
of gigabytes.

### If you have a Mac

 menu (top left) → **About This Mac**. Read two lines:

- **Chip**: it must say "Apple M1", "M2", "M3" or "M4". If it says "Intel",
  **stop here** and stay on route A — it will not run.
- **Memory**: you need **16 GB minimum**. With 8 GB it will be unusable.

### If you have a Windows PC

Press **Ctrl + Shift + Esc** to open Task Manager → **Performance** tab → click
**GPU** in the left-hand column.

- You need an **NVIDIA GeForce RTX** card (or GTX 1660 and above).
- Look at **"Dedicated GPU memory"**: you need **6 GB minimum**, 8 GB to be
  comfortable.
- If all you see is "Intel UHD Graphics" or integrated "AMD Radeon Graphics":
  **stop here**, stay on route A.

### In all cases

- **Disk space**: count on **20 GB** for the basic setup. If you let the software
  download every available model, it can climb towards 60 GB.
- A decent **internet connection**: the first launch downloads a lot.

<details>
<summary>A quick NVIDIA card reference table</summary>

| Card | Memory | Verdict |
|---|---|---|
| GTX 1050 Ti | 4 GB | it starts, but very limited |
| GTX 1660 / RTX 2060 | 6 GB | good enough |
| RTX 3060 / 4060 | 8 GB | comfortable |
| RTX 3070 / 4070 | 8–12 GB | very good |
| RTX 3090 / 4090 | 24 GB | everything unlocked |
| Apple Silicon Mac | shared memory | it works, 16 GB minimum |

</details>

---

## B.2 — Installing on Windows

This is the simplest case: **no command line at all**.

**1. Install 7-Zip** (Windows cannot open `.7z` files on its own)
→ <https://www.7-zip.org> → download, install, next-next.

**2. Update your NVIDIA drivers.** The package needs CUDA 12.8, which comes with
recent drivers. Go through the **NVIDIA App** or through
<https://www.nvidia.com/en-us/drivers/>.

**3. Download the ready-made ("portable") package:**
<https://files.acemusic.ai/acemusic/win/ACE-Step-1.5.7z>

It is big. Let it run.

**4. Unzip it.** Right-click the file → **7-Zip** → **Extract to
"ACE-Step-1.5\"**. Put the resulting folder somewhere simple, for example
`C:\ACE-Step-1.5`. **Avoid a path with accents or spaces** — it saves a lot of
trouble.

**5. Open the folder and double-click `start_gradio_ui.bat`.**

- A black window opens and scrolls text. **That is normal, do not close it** —
  that is the engine. It has to stay open while you work.
- If Windows shows "Windows protected your PC": click **More info** then **Run
  anyway**.
- The firewall may ask for permission: accept (access stays local).

**6. Wait.** On the very first launch, the models download: **30 minutes to 2
hours** depending on your connection. Subsequent times, it is a minute.

**7. Open your browser at <http://127.0.0.1:7860>** (the browser often opens on
its own). That is your studio.

---

## B.3 — Installing on a Mac (Apple Silicon)

There are **three lines to type**. Here they are word for word, plus the trick
that saves you from typing a file path by hand.

**1. Download the ready-made package:**
<https://files.acemusic.ai/acemusic/mac/ACE-Step-1.5.zip>

**2. Double-click it** to unzip. You get an `ACE-Step-1.5` folder. **Drag it into
your Home folder** (the one with your name, in the Finder sidebar).

**3. Open Terminal.** Press **Cmd + Space**, type `Terminal`, press Enter. A
window full of text opens: that is where you type.

**4. Move into the folder.** Type exactly this, **with the space after `cd`**,
then **drag and drop the `ACE-Step-1.5` folder from the Finder into the Terminal
window** — the path writes itself. Then Enter.

```
cd 
```

**5. Copy and paste these three lines, one at a time, each followed by Enter:**

```bash
xattr -dr com.apple.quarantine .
chmod +x start_gradio_ui_macos.sh
./start_gradio_ui_macos.sh
```

- The 1st removes the block macOS puts on anything that came from the internet.
- The 2nd makes the program launchable.
- The 3rd launches it.

**6. Wait.** First launch: **30 minutes to 2 hours** of downloading. **Do not
close the Terminal window**, it is what keeps the engine running.

**7. Open <http://127.0.0.1:7860> in Safari or Chrome.**

**Subsequent times**, you only redo step 4 (the `cd` + drag and drop) then the
last line, `./start_gradio_ui_macos.sh`.

---

## B.4 — First start of the studio

In the web page that opens:

1. Unfold the **Settings** panel at the top.
2. Click **Initialize Service**. That is what loads the models into memory.
   Count on one to a few minutes; a status area tells you where it is at and
   automatically detects your graphics card.
3. Go to the **Generation** tab.
4. At the top, pick the **Simple** mode.
5. Write a description in **Song Description**, for example:
   *"chanson française mélancolique, guitare acoustique, voix masculine grave"*
   (the 🎲 button gives you random examples).
6. Click **Create Sample**: the model writes the lyrics and the track sheet. Read
   it over, edit it if you want.
7. Click **Generate Music**. Count on a few minutes.

That's it. You have made a song.

When you want more control, switch **Generation Mode** to **Custom**: there you
write the style (**Caption**) and the lyrics (**Lyrics**) yourself, and you can
drop in a reference track (**Reference Audio**).

---

# Route C — The full installation, like this repo

This one really does need the terminal, and it is the one the [README](README.md)
describes: a `./song` command line with JSON presets, versioned lyrics files, and
automatic mastering.

The point: **everything is reproducible**. The same seed (`--seed`) replays
exactly the same track, a preset can be shared, a track can be touched up section
by section.

If you get that far, the simplest thing is to ask someone who codes to set it up
for you once — after that, it is commands to copy and paste. It is **not** a
necessary step to make good music.

---

# Writing a good prompt — the part that really matters

**This applies to all three routes.** This is where 90% of the quality of the
result is decided, not in the technical settings.

## 1. Describe the sound, not the artist

The model knows a huge vocabulary of genres, instruments and production terms —
but **no artist names**. Writing "in the style of Daft Punk" is literally
useless: it has no idea who that is.

❌ *"a Stromae-style song"*
✅ *"electro-pop française, synthé analogique, voix parlée-chantée, batterie sèche, mix large"*

A good description stacks **four layers**:

| Layer | Example |
|---|---|
| **Genre** | `French House`, `chanson française`, `big room house`, `indie folk` |
| **Instruments** | `basse sidechainée, nappes analogiques, piano feutré` |
| **Vocals** | `voix masculine grave`, `voix féminine aérienne`, `spoken word` |
| **Production** | `mix large, sub profond, énergie festival`, `intimiste, peu de réverbe` |

## 2. Lyrics in French, tags in English

That is the convention the model was trained on. The lyrics can be in any of the
50+ languages it handles, but **the structure tags are always written in English,
in square brackets**:

```
[Intro]

[Verse 1]
Les néons pleurent sur le bitume
Je compte les heures qui s'en vont

[Chorus]
Reviens, reviens dans la lumière

[Bridge]

[Outro]
```

Useful tags: `[Intro]`, `[Verse 1]`, `[Pre-Chorus]`, `[Chorus]`, `[Bridge]`,
`[Outro]`.
For electronic music: `[Build]`, `[Drop]`, `[Breakdown]`, `[Final Drop]`,
`[Hook]`, `[Instrumental Break]`.

**A section left empty becomes an instrumental passage.** That is how you let a
track breathe.

## 3. Making the bass drop in the right place

The model places the breaks according to **the tags**, not the words. To make a
big bass land on a specific line, isolate that line in its own `[Drop]` section,
preceded by a `[Build]`:

```
[Build]
la ligne qui monte en tension
et celle qui la suit

[Drop]
LA PHRASE QUI DOIT ENCAISSER LA BASSE
```

## 4. The rhythm of the voice is set with line breaks

There is **no** way to say "sing this syllable at 1:12". What actually affects
the delivery:

- **Line breaks** — the strongest lever. A short line is hammered out, a long
  line is crammed in.
- **Density** — little text in a long section, and the model stretches it out and
  stumbles. Fill it in, or shorten the section.
- **The prompt** — `spoken word`, `staccato`, `rapid-fire delivery`, `half-time`
  really do shift the phrasing.

## 5. Touch up rather than re-roll at random

The beginner's mistake: regenerating fifty times hoping for better. The two tools
that work:

- **Remix / retake** — you keep the track you like and move it a little. A low
  variance (0.1–0.2) gives the same track, slightly different.
- **Repaint** — you regenerate **a single section**, keeping the rest intact.
  This is the tool for the passage that is off at 1:20.

## 6. A reference track for the colour

Drop an audio file into **Reference Audio**: the model draws on it for the sonic
mood, while your lyrics and your melody stay yours. Set the strength **around
0.2** — just the mood. Higher, and you stick too closely to the reference.

---

# When it goes wrong

| Symptom | What is happening | What to do |
|---|---|---|
| **Extremely slow** | the machine is out of memory and paging to disk | **close everything else** before generating: browser with 40 tabs, Docker, virtual machines, games |
| **It crashes on load** | model too big for the card | in Settings, turn on **Offload to CPU**; pick the smallest language model (`0.6B`) |
| **The page does not open** | the engine has not finished starting | look at the black window / the Terminal: it prints the address when it is ready |
| **The voice stumbles** | not enough text for the duration | add lyrics, or shorten the track |
| **The style is ignored** | description too vague or full of proper nouns | rewrite it with the four layers: genre, instruments, vocals, production |
| **It sounds nothing like the reference** | that is intended | raise the reference strength, but you lose originality |
| **The black window closed** | the engine has stopped | relaunch `start_gradio_ui.bat` (or the Mac script) |

---

# Three things to know

**It does not stop at the first attempt.** The model's authors say it themselves:
this is not a song vending machine, it is an instrument. Good results come from a
back and forth — you listen, you adjust the description, you touch up a section.
Count on an evening to get the hang of it.

**Nothing leaves your machine** (routes B and C). The address `127.0.0.1` is your
own computer. No track, no lyric is sent anywhere. On route A, by contrast, you go
through a server: do not put anything there that you want to keep secret.

**Watch the rights if you use a reference.** A commercial track stays
copyrighted. To draw inspiration at home, nobody will mind; to publish or
monetise, that is another story.

---

# Recap

1. **Try <https://acemusic.ai> first** — two minutes, zero installation, the same
   model.
2. If you like it and your machine can take it (**NVIDIA PC with 6 GB+** or
   **Apple Silicon Mac with 16 GB+**), install the ready-made package: a few
   clicks on Windows, three lines on a Mac.
3. **Spend your time on the description and the lyrics**, not on the settings.
   Describe the sound, not the artist; lyrics in French, tags in English.
4. **Touch up** instead of re-rolling.
