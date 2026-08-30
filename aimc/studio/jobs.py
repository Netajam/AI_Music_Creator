"""The processes the studio launches, and the locks that keep them apart.

The studio reimplements neither generation nor mastering: it launches `./song`
and `./master`, which remain the single source of truth. What it adds are the
locks — and they are not the same on both sides.
"""

from __future__ import annotations

import contextlib
import json
import os
import signal
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from aimc.workspace import CACHE, DOWNLOADS, REPO_ROOT

# JSON report of the last master: `./master --report` writes it, the studio
# reads it back. Reading numbers beats re-parsing a log line by line.
MASTER_REPORT = CACHE / "last-master-report.json"

# We keep only the tail of the log: a render chatters thousands of lines, and
# only the tail says where it has got to.
LOG_KEPT = 400
LOG_SERVED = 120


class Job:
    """One generation at a time — that is the whole point of this lock."""

    busy_message = "A generation is already running."

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.proc: subprocess.Popen[str] | None = None
        self.cmd: list[str] = []
        self.log: list[str] = []
        self.started: float = 0.0
        self.finished: int | None = None

    @property
    def running(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def _before_start(self) -> None:
        """What there is to do just before launching — nothing, by default."""

    def start(self, cmd: list[str]) -> None:
        with self.lock:
            if self.running:
                raise HTTPException(409, self.busy_message)
            self._before_start()
            self.cmd, self.log, self.finished = cmd, [], None
            self.started = time.time()
            self.proc = subprocess.Popen(
                cmd, cwd=str(REPO_ROOT), stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True, bufsize=1)
            threading.Thread(target=self._pump, daemon=True).start()

    def _pump(self) -> None:
        assert self.proc and self.proc.stdout
        for line in self.proc.stdout:
            self.log.append(line.rstrip())
            del self.log[:-LOG_KEPT]
        self.finished = self.proc.wait()

    def stop(self) -> bool:
        if not self.running:
            return False
        assert self.proc
        os.kill(self.proc.pid, signal.SIGTERM)
        return True

    def state(self) -> dict[str, Any]:
        return {
            "running": self.running,
            "cmd": " ".join(self.cmd),
            "elapsed": round(time.time() - self.started) if self.started else 0,
            "started": self.started,
            "exit_code": self.finished,
            "log": self.log[-LOG_SERVED:],
        }


class MasterJob(Job):
    """One master at a time — but a master does not block a generation.

    A lock policy, decided rather than inherited. `Job` serialises generations
    because two models loaded at once exhaust the 16 GB. A master is pure
    ffmpeg: a few tens of megabytes, a few seconds, no weights in memory.
    Imposing the generation lock on it would make the button unusable for the
    ten minutes of a render, for a technical reason that does not exist.

    So it keeps its own lock, for the only reason that holds: ten clicks must
    not launch ten ffmpeg chains fighting over the disk — least of all while a
    generation actually needs the machine.
    """

    busy_message = "A master is already running."

    def _before_start(self) -> None:
        # The report describes the master under way, not the previous one.
        MASTER_REPORT.unlink(missing_ok=True)

    def state(self) -> dict[str, Any]:
        st = super().state()
        st["report"] = None
        # The report survives a studio restart: it describes the last master
        # actually written, not the last session.
        if not self.running and MASTER_REPORT.exists():
            with contextlib.suppress(json.JSONDecodeError, OSError):
                st["report"] = json.loads(MASTER_REPORT.read_text(encoding="utf-8"))
        return st


class ModelJob(Job):
    """An analysis that loads weights, run as a subprocess and handed back by file.

    Two of them now: the lyric alignment and the stem separation. They share a
    lock policy, decided like the master's and for opposite reasons. Neither is
    ffmpeg — MMS_FA loads 1.2 GB and peaks around 3 GB, measured window by
    window on tracks of 145 to 200 s; Demucs loads 320 MB and peaks at 2.3 GB,
    measured on a 200 s take. That is little next to a generation, and a lot
    next to nothing: any two of the three together have no place in 16 GB.

    Hence the subprocess rather than a thread: `./analyse` hands torch back to
    the system when it exits, where an import inside the studio would hold it
    until the tab is closed.

    And hence `_before_start`: the per-job lock only knows about its own kind,
    so it would happily start a separation on top of an alignment — two models,
    for two answers nobody is waiting for at the same time.
    """

    # What this job is called when it is the one in the way. Set per subclass:
    # the message a *sibling* raises is about this job, not about itself.
    what = "A model-backed analysis"

    _running: list[ModelJob] = []

    def __init__(self) -> None:
        super().__init__()
        # Which take this is about, and where the subprocess drops its result:
        # the route is what files it away, once the process has finished.
        self.take: str | None = None
        # Which folder that name lives in — `take` or `inspiration`. A name
        # alone stopped being enough once a separation could be asked of a
        # downloaded track: filing the result would have looked for it in
        # songs/, found nothing, and dropped the answer on the floor.
        self.source: str = "take"
        self.out: Path | None = None
        # Hand-off files the route wrote for the subprocess to read — removed
        # with the result, once it has been filed away.
        self.scratch: list[Path] = []
        ModelJob._running.append(self)

    def _before_start(self) -> None:
        for other in ModelJob._running:
            if other is not self and other.running:
                raise HTTPException(
                    409, f"{other.what} is running — one model at a time, or "
                         f"the 16 GB run out.")

    def start_for(self, take: str, out: Path, cmd: list[str],
                  scratch: list[Path] | None = None,
                  source: str = "take") -> None:
        self.take, self.source, self.out = take, source, out
        self.scratch = list(scratch or [])
        self.start(cmd)

    def state(self) -> dict[str, Any]:
        st = super().state()
        st["take"] = self.take
        st["source"] = self.source
        return st

    def cleanup(self) -> None:
        """The hand-off files, once the result has been filed away."""
        for f in (self.out, *self.scratch):
            if f is not None:
                f.unlink(missing_ok=True)


class AlignJob(ModelJob):
    """One lyric alignment at a time."""

    what = "An alignment"
    busy_message = "An alignment is already running."


class StemJob(ModelJob):
    """One stem separation at a time.

    Slower than it looks worth: about a third of the track's duration on the
    target machine — 64 s for a 200 s take, measured. Which is why nothing
    triggers it automatically, and why the studio only ever serves a result that
    is already in cache.
    """

    what = "A stem separation"
    busy_message = "A separation is already running."


class GrabJob(Job):
    """One download at a time — and it does not wait for a generation.

    The same lock policy as the master's, and for the same reason: yt-dlp and
    ffmpeg are network and disk, not weights. Making the field unusable for the
    ten minutes of a render would be a lock with no cause behind it. What it
    does hold against is ten clicks starting ten downloads into one folder.

    What it adds to `Job` is a before-and-after listing of `refs/downloads/`.
    `./grab` prints the file it wrote, but `--no-overwrites` means a URL asked
    for a second time writes nothing and prints nothing — which, in stdout
    alone, is indistinguishable from a download that never landed. The listing
    says which of the two happened, and that is the difference between "you
    already have this one" and an error message.
    """

    busy_message = "A download is already running."

    def __init__(self) -> None:
        super().__init__()
        self.url = ""
        self.before: set[str] = set()
        # What the last download actually brought in. Held rather than
        # recomputed on demand: an idle studio polls this twice a second-and-a-
        # half, and a job that has never run must report nothing rather than the
        # whole folder — every track already there would otherwise look like it
        # had just arrived.
        self.arrived: list[str] = []
        # Whether that arrival has been dealt with. The route writes down where
        # a track came from once, on the first poll after the end.
        self.settled = True

    @staticmethod
    def _listing() -> set[str]:
        return {p.name for p in DOWNLOADS.glob("*") if p.is_file()}

    def _before_start(self) -> None:
        DOWNLOADS.mkdir(parents=True, exist_ok=True)
        self.before = self._listing()
        self.arrived = []
        self.settled = False

    def start_for(self, url: str, cmd: list[str]) -> None:
        self.url = url
        self.start(cmd)

    def settle(self) -> list[str]:
        """What this download brought in — read once, when it has finished."""
        self.arrived = sorted(self._listing() - self.before)
        self.settled = True
        return self.arrived

    def state(self) -> dict[str, Any]:
        st = super().state()
        st["url"] = self.url
        st["arrived"] = list(self.arrived)
        st["settled"] = self.settled
        return st


job = Job()
master_job = MasterJob()
grab_job = GrabJob()
align_job = AlignJob()
stem_job = StemJob()


def foreign_generation() -> int | None:
    """PID of a generation launched outside the studio (a terminal, another session).

    The internal lock only sees its own launches. Without this check, the studio
    would happily start a generation on top of the terminal's — precisely the
    scenario that exhausts the 16 GB.
    """
    mine = job.proc.pid if job.proc else -1
    try:
        out = subprocess.run(["pgrep", "-f", "aimc.generation"], capture_output=True,
                             text=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    for raw in out.split():
        try:
            pid = int(raw)
        except ValueError:
            continue
        if pid not in (mine, os.getpid()):
            return pid
    return None
