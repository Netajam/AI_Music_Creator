#!/usr/bin/env python3
"""Gathers everything the night produced into one JSON record.

Three sources, joined on the slug: the collection modules (title, style, lyrics),
the ledger (what actually rendered, and how long it took) and, when it has been
run, verification.tsv (what the analyser heard back). Nothing here decides
whether a song is good; it decides what is known about it.

    python3 night/catalogue.py > night/catalogue.json
"""

from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# `aimc.workspace` is the one place that knows whether the content lives in
# this repo or in the private one cloned inside it. See its `_workspace`.
from aimc.workspace import NIGHT  # noqa: E402

COLLECTIONS = NIGHT / "collections"


def load(path: Path):
    spec = importlib.util.spec_from_file_location(f"coll_{path.stem}", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def indexed(path: Path, key: str) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as fh:
        return {r[key]: r for r in csv.DictReader(fh, delimiter="\t")}


def main() -> int:
    ledger = indexed(NIGHT / "ledger.tsv", "slug")
    checks = indexed(NIGHT / "verification.tsv", "slug")

    out = []
    for path in sorted(COLLECTIONS.glob("*.py")):
        mod = load(path)
        coll = dict(mod.COLLECTION)
        coll["slug"] = path.stem
        songs = []
        for song in mod.SONGS:
            led = ledger.get(song["slug"], {})
            chk = checks.get(song["slug"], {})
            songs.append({
                "slug": song["slug"],
                "title": song["title"],
                "bpm": song["bpm"],
                "key": song["key"],
                "duration": song["duration"],
                "language": song.get("language", "fr"),
                "instrumental": song.get("instrumental", False),
                "style": song["style"],
                "reference": song.get("reference"),
                "lyrics": song.get("lyrics", "").strip(),
                "status": led.get("status", "not rendered"),
                "seconds": int(led["seconds"]) if led.get("seconds") else None,
                "audio": led.get("audio") or None,
                "heard": {
                    "verdict": chk.get("verdict"),
                    "tempo": chk.get("tempo_heard"),
                    "sections": chk.get("sections"),
                    "drops": chk.get("drops"),
                    "bass_low": chk.get("bass_low"),
                    "bass_high": chk.get("bass_high"),
                    "notes": chk.get("notes") or "",
                } if chk else None,
            })
        coll["songs"] = songs
        out.append(coll)

    out.sort(key=lambda c: c.get("order", 99))
    rendered = sum(1 for c in out for s in c["songs"] if s["status"] == "ok")
    total = sum(len(c["songs"]) for c in out)
    json.dump({"total": total, "rendered": rendered, "collections": out},
              sys.stdout, ensure_ascii=False, indent=2)
    print(file=sys.stderr)
    print(f"{rendered}/{total} rendered across {len(out)} collections", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
