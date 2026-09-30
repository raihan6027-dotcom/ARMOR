"""Generator selection (GENERATOR=mock|diffusers|auto). See adapter.py."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.generation.adapter import GeneratedImage, GeneratorAdapter, GeneratorUnavailable
from app.generation.diffusers_adapter import DiffusersAdapter
from app.generation.mock_adapter import MockGeneratorAdapter

__all__ = [
    "GeneratedImage",
    "GeneratorAdapter",
    "GeneratorUnavailable",
    "get_generator",
    "set_generator",
]

_override: Optional[GeneratorAdapter] = None
_cached: Optional[GeneratorAdapter] = None


def _model_dir() -> str:
    return settings.generator_model_dir or str(Path(settings.model_root) / "generator" / "sd")


def _build() -> GeneratorAdapter:
    mock = MockGeneratorAdapter(settings.generator_url, settings.generator_timeout_s)
    choice = settings.generator.strip().lower()
    if choice == "mock":
        return mock
    local = DiffusersAdapter(_model_dir())
    if choice == "diffusers":
        return local
    if choice == "auto":
        return local if local.available() else mock
    raise ValueError(f"GENERATOR must be mock, diffusers, or auto (got {settings.generator!r})")


def get_generator() -> GeneratorAdapter:
    global _cached
    if _override is not None:
        return _override
    if _cached is None:
        _cached = _build()
    return _cached


def set_generator(adapter: Optional[GeneratorAdapter]) -> None:
    """Tests replace the generator; None restores the configured one."""
    global _override, _cached
    _override = adapter
    _cached = None
