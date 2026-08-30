"""What to compute on: the device, and the language model's backend."""

from __future__ import annotations


def resolve_device(requested: str) -> str:
    if requested != "auto":
        return requested
    import torch
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def resolve_backend(requested: str | None, device: str) -> str:
    if requested:
        return requested
    # MLX is the native Apple Silicon acceleration for the LM side.
    return "mlx" if device == "mps" else "vllm"
