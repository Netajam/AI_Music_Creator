"""The JSON report of a master, written even when the master failed.

The studio reads it back rather than re-parsing the log line by line: reading
numbers beats recognising sentences. A failed master must therefore write one
too, otherwise the interface would not be able to say why.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


class Report:
    """What we measured, aimed for and wrote — accumulated as the master runs."""

    def __init__(self, targets: dict[str, Any]) -> None:
        self.data: dict[str, Any] = {"targets": targets}

    def __setitem__(self, key: str, value: Any) -> None:
        self.data[key] = value

    def __getitem__(self, key: str) -> Any:
        return self.data[key]

    def emit(self, destination: str | None, code: int) -> int:
        """Write the report if one was asked for, and return the exit code."""
        if not destination:
            return code
        self.data["exit_code"] = code
        try:
            Path(destination).expanduser().write_text(
                json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as exc:
            print(f"  report not written: {exc}", file=sys.stderr)
        return code
