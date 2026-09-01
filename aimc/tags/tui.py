"""The composer's screen: the facts on the left, what you are writing below.

Built on `rich` alone, which the engine's environment already has. rich draws;
it does not read keys, so this is a prompt loop rather than a full-screen app —
which suits the job, because writing a style is typing, not navigating.
"""

from __future__ import annotations

from pathlib import Path

from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.table import Table
from rich.text import Text

from aimc.tags import vocab
from aimc.tags.compose import (
    MOODS,
    NEGATIVES,
    PRODUCTION,
    STYLE_MAX,
    VOICES,
    Style,
    usage,
)
from aimc.tags.genres import Genre, search

console = Console()


def _menu(title: str, options: tuple[str, ...], allow_free: bool = True) -> str:
    """Numbered choices, with typing your own always available."""
    table = Table(show_header=False, box=None, padding=(0, 1))
    for i, option in enumerate(options, 1):
        table.add_row(f"[dim]{i:>2}[/]", option)
    console.print(Panel(table, title=title, title_align="left", border_style="dim"))
    hint = "number, your own words, or blank to skip"
    while True:
        answer = Prompt.ask(f"  [bold]{title}[/]", default="", show_default=False)
        answer = answer.strip()
        if not answer:
            return ""
        if answer.isdigit() and 1 <= int(answer) <= len(options):
            return options[int(answer) - 1]
        if allow_free:
            return answer
        console.print(f"  [yellow]{hint}[/]")


def show_genre(genre: Genre) -> None:
    """Everything the database knows, in the order it is useful while writing."""
    facts = Table(show_header=False, box=None, padding=(0, 1))
    facts.add_row("[dim]tempo[/]", f"[bold]{genre.bpm}[/] BPM")
    if genre.year:
        facts.add_row("[dim]from[/]", f"{genre.place or 'unrecorded'}, {genre.year}")
    for slug, inherited in genre.lineage[:2]:
        facts.add_row("[dim]after[/]", f"{slug} — {inherited[:90]}")
    if genre.curators:
        facts.add_row("[dim]curated[/]", ", ".join(genre.curators))
    if genre.aliases:
        facts.add_row("[dim]also[/]", ", ".join(genre.aliases))

    body = [facts]
    if genre.description:
        body.append(Text(genre.description, style="italic"))
    if genre.tracks:
        listing = Table(show_header=False, box=None, padding=(0, 1))
        for artist, title in genre.tracks[:5]:
            listing.add_row(f"[dim]{artist}[/]", title)
        body.append(Panel(listing, title="what a curator picked", title_align="left",
                          border_style="dim"))
    console.print(Panel(Columns(body, expand=True), title=f"[bold]{genre.name}[/]",
                        title_align="left", border_style="cyan"))


def choose_genre(genres: list[Genre]) -> Genre | None:
    """Search, then pick. Blank search lists everything."""
    if not genres:
        console.print(Panel(
            "No genre database. It lives in [bold]refs/waxonia/[/] in the "
            "workspace, and without it you can still write a style by hand — "
            "you lose the tempo bands and the eras, not the tool.",
            border_style="yellow"))
        return None
    while True:
        query = Prompt.ask("\n  [bold]genre[/] [dim](name, alias, city, curator; "
                           "blank for all, q to stop)[/]", default="")
        if query.strip().lower() in {"q", "quit"}:
            return None
        found = search(genres, query)
        if not found:
            console.print("  [yellow]nothing matches that[/]")
            continue
        table = Table(box=None, padding=(0, 2))
        table.add_column("", style="dim", justify="right")
        table.add_column("genre", style="bold")
        table.add_column("BPM")
        table.add_column("from", style="dim")
        for i, g in enumerate(found[:30], 1):
            table.add_row(str(i), g.name, g.bpm,
                          f"{g.place}, {g.year}" if g.year else "")
        console.print(table)
        if len(found) > 30:
            console.print(f"  [dim]…and {len(found) - 30} more; narrow the search[/]")
        pick = Prompt.ask("  [bold]number[/] [dim](or blank to search again)[/]",
                          default="")
        if pick.strip().isdigit() and 1 <= int(pick) <= min(len(found), 30):
            return found[int(pick) - 1]


def show_style(style: Style) -> None:
    """What is written so far, fragment by fragment, marked against the model."""
    rendered = style.render()
    if not rendered:
        console.print("  [dim]nothing written yet[/]")
        return
    table = Table(show_header=False, box=None, padding=(0, 1))
    for part, is_known in vocab.check(rendered):
        mark = "[green]✓[/]" if is_known else "[dim]·[/]"
        table.add_row(mark, part)
    over = style.over
    count = (f"[red]{style.length} / {STYLE_MAX} — {over} over, the CLI will "
             f"refuse this[/]" if over > 0 else
             f"[dim]{style.length} / {STYLE_MAX} characters[/]")
    console.print(Panel(table, title="the style so far", title_align="left",
                        subtitle=count, subtitle_align="right",
                        border_style="red" if over > 0 else "green"))
    console.print("  [dim]✓ marks a term the model has in its 178,571-entry "
                  "vocabulary. Unmarked is not wrong — most prose is unmarked — "
                  "it simply has no evidence behind it.[/]")


def warn_repetition(presets: Path) -> None:
    """Say what the workspace has been asking for, before it is asked again."""
    counts, seen = usage(presets)
    if seen < 8 or not counts:
        return
    top, n = counts.most_common(1)[0]
    if n / seen < 0.6:
        return
    console.print(Panel(
        f"[yellow]{n} of the last {seen} presets here say “{top}”.[/]\n"
        f"That is the shape docs/variety.md records: a wide tempo range, "
        f"genuinely different genres, and one songwriter underneath them all. "
        f"Worth picking something else this time.",
        border_style="yellow"))


def choose_negative() -> str:
    """Pick from the groups that have earned their place, or write your own."""
    table = Table(show_header=False, box=None, padding=(0, 1))
    keys = list(NEGATIVES)
    for i, key in enumerate(keys, 1):
        table.add_row(f"[dim]{i:>2}[/]", f"[bold]{key}[/]", f"[dim]{NEGATIVES[key]}[/]")
    console.print(Panel(table, title="negative — what the model must avoid",
                        title_align="left", border_style="dim"))
    answer = Prompt.ask("  [bold]numbers[/] [dim](comma-separated), your own "
                        "words, or blank[/]", default="")
    answer = answer.strip()
    if not answer:
        return ""
    picked = [n.strip() for n in answer.split(",")]
    if all(p.isdigit() and 1 <= int(p) <= len(keys) for p in picked):
        chosen = [NEGATIVES[keys[int(p) - 1]] for p in picked]
        return ", ".join(dict.fromkeys(", ".join(chosen).split(", ")))
    return answer


def build_style(genre: Genre | None) -> Style:
    """The guided pass. Every field is skippable; none of them is a rule."""
    style = Style()

    default_genre = genre.name.lower() if genre else ""
    style.genre = Prompt.ask("\n  [bold]genre words[/]", default=default_genre)
    if genre and genre.year:
        style.era = Prompt.ask("  [bold]era[/]",
                               default=f"{genre.year} {genre.place}".strip())
    else:
        style.era = Prompt.ask("  [bold]era[/]", default="")

    console.print("\n  [dim]instruments — one per line, blank line to finish. "
                  "Each is checked against the vocabulary as you go.[/]")
    while True:
        item = Prompt.ask("  [bold]+[/]", default="")
        if not item.strip():
            break
        mark = "[green]✓ in the vocabulary[/]" if vocab.known(item) else ""
        near = vocab.suggest(item, 4)
        console.print(f"    {mark}" if mark else
                      f"    [dim]not a vocabulary term"
                      f"{'; near it: ' + ', '.join(near) if near else ''}[/]")
        style.instruments.append(item.strip())

    style.voice = _menu("voice", VOICES)
    style.production = _menu("production", PRODUCTION)
    style.mood = _menu("mood", MOODS)
    return style


def confirm_write(path: Path, body: str) -> bool:
    console.print(Panel(body, title=str(path), title_align="left",
                        border_style="green"))
    return Confirm.ask(f"  write [bold]{path.name}[/]?", default=True)


def ask_int(label: str, default: int | None) -> int | None:
    if default is None:
        answer = Prompt.ask(f"  [bold]{label}[/]", default="")
        return int(answer) if answer.strip().isdigit() else None
    return IntPrompt.ask(f"  [bold]{label}[/]", default=default)
