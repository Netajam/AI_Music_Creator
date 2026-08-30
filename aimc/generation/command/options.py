"""The command line of `./song`, one option group per purpose.

The parser is 160 lines because there are 45 options, not because it is
complicated. Split into groups, each one fits on screen and reads next to what
it drives — and adding an option no longer means finding its place in the middle
of everything else.
"""

from __future__ import annotations

import argparse

from aimc.generation.catalog import (
    AUDIO_FORMATS,
    BPM_RANGE,
    DEFAULT_DIT,
    DEFAULT_LM,
    DURATION_RANGE,
    STYLE_MAX_CHARS,
    TRACK_NAMES,
)
from aimc.workspace import SONGS

EPILOG = """examples:
  # a French song from a lyrics file
  ./song --style "chanson française mélancolique, guitare acoustique, voix masculine" \\
         --lyrics lyrics/exemple.txt --bpm 90 --duration 150

  # the same, but "in the style of" an existing track
  ./song --preset presets/exemple.json --reference ~/Music/track.mp3 --style-strength 0.25

  # a cover of an existing track in another style
  ./song --cover ~/Music/track.mp3 --style "version jazz piano-voix" --lyrics lyrics/exemple.txt
"""


def _content(p: argparse.ArgumentParser) -> None:
    src = p.add_argument_group("content")
    src.add_argument("--preset", metavar="FILE.json",
                     help="JSON preset supplying the default values")
    src.add_argument("--style", metavar="TEXT",
                     help=f"description of the musical style (the main prompt, "
                          f"<{STYLE_MAX_CHARS} characters)")
    src.add_argument("--lyrics", metavar="FILE",
                     help="text file holding the lyrics (UTF-8)")
    src.add_argument("--lyrics-text", metavar="TEXT",
                     help="lyrics given directly, instead of --lyrics")
    src.add_argument("--instrumental", action="store_true",
                     help="instrumental track, no vocals")
    src.add_argument("--language", default="fr", metavar="CODE",
                     help="language of the singing, ISO 639-1 code (default: fr)")


def _music(p: argparse.ArgumentParser) -> None:
    mus = p.add_argument_group("music")
    mus.add_argument("--bpm", type=int, metavar="N",
                     help=f"tempo, {BPM_RANGE[0]}-{BPM_RANGE[1]} "
                          f"(default: chosen by the model)")
    mus.add_argument("--key", metavar="KEY",
                     help='key, e.g. "C major", "F# minor"')
    mus.add_argument("--time-signature", metavar="N",
                     help="time signature: 2, 3, 4 or 6")
    mus.add_argument("--duration", type=float, metavar="SECONDS",
                     help=f"target duration, {DURATION_RANGE[0]}-{DURATION_RANGE[1]} "
                          f"(default: chosen by the model)")


def _reference(p: argparse.ArgumentParser) -> None:
    ref = p.add_argument_group("reference audio")
    ref.add_argument("--reference", metavar="AUDIO",
                     help="reference track: generates a NEW song in a similar style")
    ref.add_argument("--cover", metavar="AUDIO",
                     help="source track: makes a COVER of it (task_type=cover)")
    ref.add_argument("--style-strength", type=float, metavar="F",
                     help="influence of the audio (0.0-1.0). ~0.2 for a plain style "
                          "transfer, higher to stay close to the original")


def _retake(p: argparse.ArgumentParser) -> None:
    # Take up a take you like and vary it a little, rather than rolling a new
    # random seed and losing everything.
    var = p.add_argument_group("variations on an existing take")
    var.add_argument("--retake-seed", type=int, metavar="N",
                     help="seed of the take to vary (typically the --seed of a track "
                          "you want to touch up rather than redo)")
    var.add_argument("--retake-variance", type=float, default=None, metavar="F",
                     help="amplitude of the variation, 0.0-1.0. 0.1-0.2 = the same track "
                          "nudged slightly, 0.5+ = a reinterpretation")


def _repaint(p: argparse.ArgumentParser) -> None:
    # Regenerate ONE section of an existing track, keeping the rest.
    rep = p.add_argument_group("touching up a section (repaint)")
    rep.add_argument("--repaint", metavar="AUDIO",
                     help="track to touch up: regenerates only the interval given")
    rep.add_argument("--repaint-from", type=float, default=None, metavar="SECONDS",
                     help="start of the section to regenerate")
    rep.add_argument("--repaint-to", type=float, default=None, metavar="SECONDS",
                     help="end of the section to regenerate (-1 = to the very end)")
    rep.add_argument("--repaint-mode", choices=["conservative", "balanced", "aggressive"],
                     default=None,
                     help="how far to stray from the original (default: balanced)")
    rep.add_argument("--repaint-strength", type=float, default=None, metavar="F",
                     help="in balanced mode: 0.0 = aggressive, 1.0 = conservative")


def _lego(p: argparse.ArgumentParser) -> None:
    # Add an instrument track to an existing song, without touching the rest.
    # The engine calls this "lego"; it honours the repaint interval, so the
    # addition can cover only one section.
    leg = p.add_argument_group("adding an instrument track (lego)")
    leg.add_argument("--lego", metavar="AUDIO",
                     help="track to add a part to: the rest is preserved")
    leg.add_argument("--lego-track", choices=TRACK_NAMES, default=None, metavar="TRACK",
                     help="track to add: " + ", ".join(TRACK_NAMES))
    leg.add_argument("--lego-from", type=float, default=None, metavar="SECONDS",
                     help="start of the interval to add the track over (default: 0)")
    leg.add_argument("--lego-to", type=float, default=None, metavar="SECONDS",
                     help="end of the interval (-1 or omitted = to the very end)")


def _language_model(p: argparse.ArgumentParser) -> None:
    lm = p.add_argument_group("steering the language model (structure/arrangement)")
    lm.add_argument("--lm-temperature", type=float, default=None, metavar="F",
                    help="creativity of the arrangement, 0.0-2.0 (default: 0.85). "
                         "Higher = more surprising structures, less stable")
    lm.add_argument("--lm-top-p", type=float, default=None, metavar="F",
                    help="the LM's nucleus sampling (default: 0.9)")
    lm.add_argument("--lm-cfg", type=float, default=None, metavar="F",
                    help="LM guidance (default: 2.0). THIS is the setting that makes it "
                         "follow the prompt, not --guidance: turbo ignores diffusion CFG")
    lm.add_argument("--negative", metavar="TEXT", default=None,
                    help="the LM's negative prompt: what we do NOT want to hear")


def _generation(p: argparse.ArgumentParser) -> None:
    gen = p.add_argument_group("generation")
    gen.add_argument("--steps", type=int, default=8, metavar="N",
                     help="diffusion steps (default: 8, suited to the turbo model)")
    gen.add_argument("--seed", type=int, default=-1, metavar="N",
                     help="random seed; -1 = random (default)")
    gen.add_argument("--count", type=int, default=1, metavar="N",
                     help="number of variants to generate (default: 1; 2+ doubles the memory)")
    gen.add_argument("--format", default="wav", choices=AUDIO_FORMATS,
                     help="output format (default: wav, lossless). A take is born "
                          "lossless or it never will be: mp3, opus and aac are "
                          "listening formats, NOT deliverables — ./master refuses them, "
                          "and converting them back to wav restores nothing. A 145 s wav "
                          "weighs ~28 MB against ~2.3 MB as mp3: that is the price of "
                          "publishing")
    gen.add_argument("--out", metavar="FOLDER", default=str(SONGS),
                     help=f"output folder (default: {SONGS})")
    gen.add_argument("--no-thinking", action="store_true",
                     help="disables the LM's CoT reasoning (faster, worse)")
    gen.add_argument("--timeout", type=int, default=1800, metavar="SECONDS",
                     help="maximum time for the diffusion loop (default: 1800). "
                          "The engine imposes 600 s, too short here: a 145 s track "
                          "already needs ~350 s of diffusion, and more if the machine "
                          "starts swapping")
    gen.add_argument("--sampler", choices=["euler", "heun"], default=None,
                     help="euler = 1st order (default, fast); heun = 2nd order, cleaner "
                          "but about twice as slow")
    gen.add_argument("--infer-method", choices=["ode", "sde"], default=None,
                     help="ode = deterministic (default); sde = stochastic, more variety")
    gen.add_argument("--shift", type=float, default=None, metavar="F",
                     help="timestep shift (default: 1.0). >1 concentrates the computation "
                          "on the overall structure, <1 on the details")


def _finishing(p: argparse.ArgumentParser) -> None:
    fin = p.add_argument_group("audio finishing")
    fin.add_argument("--fade-in", type=float, default=None, metavar="SECONDS",
                     help="fade in (default: 0)")
    fin.add_argument("--fade-out", type=float, default=None, metavar="SECONDS",
                     help="fade out (default: 0)")
    fin.add_argument("--normalize-db", type=float, default=None, metavar="DB",
                     help="target peak level, e.g. -1.0 (default) or -3.0 for more headroom")
    fin.add_argument("--no-normalize", action="store_true",
                     help="disables level normalisation")


def _advanced(p: argparse.ArgumentParser) -> None:
    adv = p.add_argument_group("advanced / memory")
    adv.add_argument("--dit", default=DEFAULT_DIT, metavar="NAME",
                     help=f"DiT model (default: {DEFAULT_DIT})")
    adv.add_argument("--lm", default=DEFAULT_LM, metavar="NAME",
                     help=f"5Hz language model (default: {DEFAULT_LM})")
    adv.add_argument("--no-lm", action="store_true",
                     help="does not use the LM (less memory, lower quality)")
    adv.add_argument("--no-dcw", action="store_true",
                     help="turns off the wavelet correction (DCW), which the engine "
                          "enables for turbo models. A suspect when a CUDA card "
                          "without bfloat16 returns NaN latents")
    adv.add_argument("--offload", action="store_true",
                     help="offloads the weights to the CPU between steps (if memory is tight)")
    adv.add_argument("--mlx-dit", action="store_true",
                     help="enables the MLX DiT. OFF BY DEFAULT: the MLX conversion also "
                          "keeps the PyTorch copy in memory (~9.5 GB each in float32) and "
                          "blows past the 16 GB. Only enable it on a bigger machine")
    adv.add_argument("--device", default="auto",
                     choices=["auto", "mps", "cpu", "cuda"],
                     help="compute device (default: auto -> mps on a Mac)")
    adv.add_argument("--backend", default=None, choices=["mlx", "pt", "vllm"],
                     help="the LM's backend (default: mlx on Apple Silicon)")
    adv.add_argument("--dry-run", action="store_true",
                     help="validates and prints the parameters without loading or generating")


# The order matters: it is the order of the groups in `--help`.
GROUPS = (_content, _music, _reference, _retake, _repaint, _lego,
          _language_model, _generation, _finishing, _advanced)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="song",
        description="Generates a song locally with ACE-Step 1.5.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=EPILOG,
    )
    for group in GROUPS:
        group(p)
    return p
