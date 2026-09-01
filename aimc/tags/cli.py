"""./tags — compose a style against the genre database and the model's vocabulary.

    ./tags                       browse, compose, write a preset
    ./tags acid-house            start on that genre
    ./tags --list                what the database holds
    ./tags --curators            who curated what
    ./tags --check "dub techno, tape delay, instrumental"

It writes a preset and nothing else. Rendering it is `./song --preset …`, which
is deliberate: this is the writing desk, and the machine that costs minutes per
take is somewhere else.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from aimc.tags import vocab
from aimc.tags.compose import preset
from aimc.tags.genres import Genre, curators, load, search
from aimc.workspace import PRESETS, unique_path


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="./tags", description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("genre", nargs="?", default="",
                   help="start on this genre (name, slug or alias)")
    p.add_argument("--list", action="store_true",
                   help="list the genres and their tempo bands, then stop")
    p.add_argument("--curators", action="store_true",
                   help="list the curators and what they curated, then stop")
    p.add_argument("--check", metavar="STYLE",
                   help="mark each fragment of a style against the vocabulary")
    p.add_argument("--out", metavar="FOLDER", default=None,
                   help=f"where to write the preset (default: {PRESETS})")
    return p


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9-]+", "-", name.lower()).strip("-") or "sans-titre"


def _listing(genres: list[Genre]) -> int:
    from rich.table import Table

    from aimc.tags.tui import console

    table = Table(box=None, padding=(0, 2))
    for column in ("genre", "BPM", "from", "aliases"):
        table.add_column(column, style="bold" if column == "genre" else "")
    for g in genres:
        table.add_row(g.name, g.bpm, f"{g.place}, {g.year}" if g.year else "",
                      ", ".join(g.aliases[:3]))
    console.print(table)
    console.print(f"  [dim]{len(genres)} genres[/]")
    return 0


def _curators(genres: list[Genre]) -> int:
    from aimc.tags.tui import console

    by_name = curators(genres)
    if not by_name:
        console.print("  [dim]no curator is named in this database[/]")
        return 0
    for name, curated in by_name.items():
        console.print(f"  [bold]{name}[/]  [dim]{len(curated)} genres[/]")
        console.print(f"    {', '.join(g.name for g in curated)}\n")
    return 0


def _check(style: str) -> int:
    from aimc.tags.tui import console

    if not vocab.load():
        print("No vocabulary: engine/ has not been cloned.", file=sys.stderr)
        return 1
    for part, is_known in vocab.check(style):
        mark = "[green]✓[/]" if is_known else "[dim]·[/]"
        console.print(f"  {mark} {part}")
    return 0


def main() -> int:
    args = build_parser().parse_args()
    genres = load()

    if args.list:
        return _listing(genres)
    if args.curators:
        return _curators(genres)
    if args.check:
        return _check(args.check)

    from rich.prompt import Confirm, Prompt

    from aimc.tags import tui

    tui.console.print()
    if not vocab.load():
        tui.console.print("  [yellow]No vocabulary: engine/ has not been cloned, "
                          "so nothing can be marked as known.[/]")

    chosen: Genre | None = None
    if args.genre:
        found = search(genres, args.genre)
        chosen = found[0] if found else None
        if chosen is None:
            tui.console.print(f"  [yellow]no genre matches “{args.genre}”[/]")
    if chosen is None:
        chosen = tui.choose_genre(genres)
    if chosen is not None:
        tui.show_genre(chosen)

    out_dir = Path(args.out) if args.out else PRESETS
    tui.warn_repetition(out_dir)

    style = tui.build_style(chosen)
    tui.show_style(style)
    negative = tui.choose_negative()

    tui.console.print()
    bpm = tui.ask_int("bpm", chosen.mid_bpm if chosen else None)
    key = Prompt.ask("  [bold]key[/]", default="")
    duration = tui.ask_int("duration (seconds)", 180) or 180
    language = Prompt.ask("  [bold]language[/]", default="fr")
    instrumental = Confirm.ask("  [bold]instrumental?[/]", default=False)
    lyrics = "" if instrumental else Prompt.ask(
        "  [bold]lyrics file[/] [dim](relative to the preset, blank for none)[/]",
        default="")

    name = Prompt.ask("\n  [bold]name[/]",
                          default=_slug(chosen.name) if chosen else "sans-titre")
    body = preset(style, negative, bpm, key, duration, language,
                  instrumental, lyrics or None)
    text = json.dumps(body, ensure_ascii=False, indent=2) + "\n"

    out_dir.mkdir(parents=True, exist_ok=True)
    path = unique_path(out_dir / f"{_slug(name)}.json")
    if not tui.confirm_write(path, text):
        tui.console.print("  [dim]nothing written[/]")
        return 0
    path.write_text(text, encoding="utf-8")
    tui.console.print(f"\n  wrote [bold]{path}[/]")
    tui.console.print(f"  [dim]./song --preset {path} --seed 1[/]\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
