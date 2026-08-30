#!/usr/bin/env python3
"""The night worker: drains night/queue/ in ONE process, models loaded once.

Why this exists. Rendering a song through `./song` costs about three and a half
minutes of model loading before the first diffusion step, and that price is paid
again for every take because every take is a new process. Over a hundred songs
that is five and a half hours of loading the same two checkpoints. This script
loads the DiT and the 5Hz LM once and then walks the queue.

It is deliberately built out of the same pieces `./song` uses — the same parser,
the same preset merge, the same validation, the same params, the same manifest —
so a take rendered here is indistinguishable from a take rendered by hand, and
the settings file beside it says the same things. It reaches into two private
helpers of `aimc.generation.render.engine` to do it; that is the price of not
forking the render path, and it is the right way round.

One generation at a time remains a hard constraint of this machine, so this is a
strictly serial loop. The device cache is emptied between takes: the documented
out-of-memory came from two takes in a single graph, and nothing here shares one.

On the Mac this loop was measured and reverted — 16 GiB cannot hold a DiT twice,
and `night/runner.sh` (one process per take) is what runs here. It is kept, and
now works on CUDA too, because the reason it lost is a memory ceiling that a
rented GPU does not have: on Colab, loading the models once is the whole point.
See `colab/README.md`.

Success is decided by a file on disk, never by an exit code — `./song` is
documented to exit 0 after an out-of-memory that wrote nothing.
"""

from __future__ import annotations

import argparse
import gc
import json
import os
import shlex
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from aimc.generation.command import (  # noqa: E402
    apply_preset,
    build_parser,
    inherit_from_source,
    resolve_lyrics,
    validate,
)
from aimc.workspace import NIGHT, SONGS, WORKSPACE  # noqa: E402

# The machinery is `night/*.py` under ROOT; everything it reads and writes is
# under the workspace, which is ROOT again unless a second repo holds it.
QUEUE = NIGHT / "queue"
DONE = NIGHT / "done"
FAILED = NIGHT / "failed"
LOGS = NIGHT / "logs"
LEDGER = NIGHT / "ledger.tsv"


def next_job() -> Path | None:
    jobs = sorted(QUEUE.glob("*.json"))
    return jobs[0] if jobs else None


def options() -> argparse.Namespace:
    """The worker's own arguments, which are not a job's arguments.

    `--extra` exists for what belongs to the machine rather than to the song:
    `--backend pt` on a GPU too old for nano-vllm, `--device cuda` where the
    detection would have to guess. It is appended after the job's own `extra`,
    so a job that already says something keeps saying it and the machine only
    gets the last word on what the job left unspecified.
    """
    p = argparse.ArgumentParser(description="drain night/queue/, models loaded once")
    p.add_argument("--extra", default="", metavar="ARGS",
                   help="extra ./song arguments added to every job in the queue")
    return p.parse_args()


def free_cache(torch: Any, device: str) -> None:
    """Hand the take's memory back before the next one asks for it.

    `torch.mps` exists on a CUDA build and `torch.cuda` on a Mac one, so the
    attribute is no evidence of anything: the device we actually loaded on is.
    """
    if device == "mps" and hasattr(torch, "mps"):
        torch.mps.empty_cache()
    elif device == "cuda" and torch.cuda.is_available():
        torch.cuda.empty_cache()


def args_for(job: dict, extra: str = "") -> tuple:
    """The very command line ./song would have been given, parsed and validated."""
    argv = ["--preset", str(WORKSPACE / job["preset"]), "--seed", str(job["seed"]),
            "--steps", str(job["steps"]),
            "--out", str(SONGS / "night" / job["collection"])]
    argv += shlex.split(job.get("extra", ""))
    argv += shlex.split(extra)
    parser = build_parser()
    args = parser.parse_args(argv)
    apply_preset(args, parser)
    inherit_from_source(args)
    validate(args, parser)
    return args, resolve_lyrics(args, parser)


def record(job: dict, status: str, secs: int, audio: str) -> None:
    if not LEDGER.exists():
        LEDGER.write_text("finished_at\tslug\tcollection\tstatus\tseconds\taudio\tlog\n")
    with LEDGER.open("a", encoding="utf-8") as fh:
        fh.write(f"{datetime.now():%F %T}\t{job['slug']}\t{job['collection']}\t"
                 f"{status}\t{secs}\t{audio}\tnight/worker-console.log\n")


def main() -> int:
    from aimc.generation.render.engine import _load_dit, _load_lm, _prepare_environment
    from aimc.generation.render.manifest import write_manifest
    from aimc.generation.render.naming import final_name
    from aimc.generation.render.params import build_config, build_params
    from aimc.workspace import unique_path

    opts = options()

    first = next_job()
    if first is None:
        print("queue empty — nothing to do")
        return 0

    args, _ = args_for(json.loads(first.read_text()), opts.extra)
    device, backend = _prepare_environment(args)
    from acestep.inference import generate_music  # noqa: PLC0415

    print(f"loading models once on {device} (LM backend {backend})…", flush=True)
    t0 = time.time()
    dit = _load_dit(args, device)
    if dit is None:
        print("DiT failed to load — nothing can follow", file=sys.stderr)
        return 1
    llm = _load_lm(args, device, backend)
    print(f"models ready in {time.time() - t0:.0f}s\n", flush=True)

    import torch  # noqa: PLC0415

    rendered = 0
    while (job_path := next_job()) is not None:
        job = json.loads(job_path.read_text())
        slug, coll = job["slug"], job["collection"]
        print(f"▶ {datetime.now():%F %T}  {coll}/{slug}  "
              f"(seed {job['seed']}, steps {job['steps']})", flush=True)
        start = time.time()
        audio_out = ""
        staging = SONGS / "night" / coll / f".run-{slug}-{time.strftime('%Y%m%d-%H%M%S')}"
        try:
            args, lyrics = args_for(job, opts.extra)
            params = build_params(args, lyrics, dit.generate_instruction)
            config = build_config(args)
            out_dir = Path(args.out)
            out_dir.mkdir(parents=True, exist_ok=True)
            stamp = time.strftime("%Y%m%d-%H%M%S")
            staging = out_dir / f".run-{slug}-{stamp}"
            staging.mkdir(parents=True, exist_ok=True)

            result = generate_music(dit, llm, params, config, save_dir=str(staging))
            if result.success:
                for audio in result.audios:
                    produced = Path(audio["path"])
                    if not produced.exists():
                        continue
                    target = unique_path(out_dir / final_name(args, produced, stamp))
                    shutil.move(str(produced), str(target))
                    write_manifest(target, args, params, config, lyrics, device, backend)
                    audio_out = os.path.relpath(target.resolve(), WORKSPACE)
            else:
                print(f"  engine says: {getattr(result, 'error', 'reason unknown')}",
                      file=sys.stderr)
        except Exception as exc:  # noqa: BLE001 — one bad job must not end the night
            print(f"  raised: {exc!r}", file=sys.stderr)
        finally:
            shutil.rmtree(staging, ignore_errors=True)

        secs = int(time.time() - start)
        ok = bool(audio_out) and (WORKSPACE / audio_out).stat().st_size > 0
        record(job, "ok" if ok else "FAILED", secs, audio_out)
        shutil.move(str(job_path), str((DONE if ok else FAILED) / job_path.name))
        print(f"  {'ok' if ok else 'FAILED'}  {secs}s  {audio_out or '(nothing written)'}\n",
              flush=True)
        rendered += 1

        gc.collect()
        free_cache(torch, device)

    print(f"queue empty — {rendered} take(s) this run, stopping at {datetime.now():%F %T}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
