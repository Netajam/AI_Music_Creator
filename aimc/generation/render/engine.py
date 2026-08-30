"""The bridge to ACE-Step: load the models, generate, file the outputs away.

This is the only module in the repo that imports `acestep`, and it only does so
once the arguments have been validated. Everything before it — help, validation,
preset, recap — stays instant and reserves no memory.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any

from aimc.generation.render.manifest import write_manifest
from aimc.generation.render.naming import final_name
from aimc.generation.render.params import build_config, build_params
from aimc.generation.render.runtime import resolve_backend, resolve_device
from aimc.generation.render.summary import describe
from aimc.workspace import CHECKPOINT_DIR, ENGINE_ROOT, unique_path


def _prepare_environment(args: argparse.Namespace) -> tuple[str, str]:
    """Put engine/ on the path, set up the environment, and pick the compute."""
    # engine/ has to be on sys.path and serve as the project root: that is where
    # the acestep package and the checkpoints/ folder live.
    sys.path.insert(0, str(ENGINE_ROOT))
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    os.environ["ACESTEP_GENERATION_TIMEOUT"] = str(args.timeout)

    device = resolve_device(args.device)
    backend = resolve_backend(args.backend, device)
    if backend == "mlx":
        os.environ["ACESTEP_LM_BACKEND"] = "mlx"
    return device, backend


def _load_dit(args: argparse.Namespace, device: str) -> Any | None:
    """The diffusion model. None if loading failed — nothing follows."""
    from acestep.handler import AceStepHandler

    handler = AceStepHandler()
    print(f"Loading the DiT ({args.dit}) on {device}…", flush=True)
    status, ready = handler.initialize_service(
        project_root=str(ENGINE_ROOT),
        config_path=args.dit,
        device=device,
        offload_to_cpu=args.offload,
        use_mlx_dit=args.mlx_dit,
    )
    if not ready:
        print(f"DiT failed to load: {status}", file=sys.stderr)
        return None
    return handler


def _load_lm(args: argparse.Namespace, device: str, backend: str) -> Any:
    """The language model, which decides the structure and the arrangement.

    Its failure is not fatal: the DiT can generate without it, less well. We say
    so and carry on, rather than throwing away the DiT load already done.
    """
    from acestep.llm_inference import LLMHandler

    handler = LLMHandler()
    if args.no_lm:
        return handler
    print(f"Loading the 5Hz LM ({args.lm}, backend {backend})…", flush=True)
    status, ok = handler.initialize(
        checkpoint_dir=str(CHECKPOINT_DIR),
        lm_model_path=args.lm,
        backend=backend,
        device=device,
        offload_to_cpu=args.offload,
    )
    if not ok:
        print(f"Warning: LM not loaded ({status}). "
              f"Generation continues without it.", file=sys.stderr)
    return handler


def _collect(result: Any, out_dir: Path, args: argparse.Namespace, stamp: str,
             params: Any, config: Any, lyrics: str, device: str,
             backend: str) -> None:
    """Move each take out of the working folder under a never-reused name."""
    print("\nDone:")
    for audio in result.audios:
        produced = Path(audio["path"])
        if not produced.exists():
            print(f"  (not found: {produced})", file=sys.stderr)
            continue
        target = unique_path(out_dir / final_name(args, produced, stamp))
        shutil.move(str(produced), str(target))
        manifest = write_manifest(target, args, params, config, lyrics, device, backend)
        print(f"  {target}")
        print(f"  {manifest.name}  (settings for this take)")


def run(args: argparse.Namespace, lyrics: str) -> int:
    device, backend = _prepare_environment(args)
    describe(args, lyrics, device, backend)

    from acestep.inference import generate_music

    dit_handler = _load_dit(args, device)
    if dit_handler is None:
        return 1
    llm_handler = _load_lm(args, device, backend)

    params = build_params(args, lyrics, dit_handler.generate_instruction)
    config = build_config(args)

    out_dir = Path(args.out).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)

    # The engine writes under a name derived from the parameters: two identical
    # runs would aim at the same file. So we isolate it in a temporary folder,
    # then move the result out under a name that is never reused.
    stamp = time.strftime("%Y%m%d-%H%M%S")
    staging = out_dir / f".run-{os.getpid()}-{stamp}"
    staging.mkdir(parents=True, exist_ok=True)

    print("Generating… (expect a few minutes on an M2 Pro)\n", flush=True)
    result = generate_music(dit_handler, llm_handler, params, config,
                            save_dir=str(staging))

    if not result.success:
        shutil.rmtree(staging, ignore_errors=True)
        print(f"Generation failed: {getattr(result, 'error', 'reason unknown')}",
              file=sys.stderr)
        return 1

    _collect(result, out_dir, args, stamp, params, config, lyrics, device, backend)
    shutil.rmtree(staging, ignore_errors=True)
    return 0
