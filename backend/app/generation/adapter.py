"""GeneratorAdapter: the swappable generative AI behind ARMOR.

ARMOR calls a generator only after the policy engine returned ALLOW, and every
result then goes through the Output Guard and ARMOR Shield. Adapters:

    mock       generator_mock/ service over HTTP (default; a SIMULATION, runs offline
               on any laptop)
    diffusers  a real local Stable Diffusion model (optional; needs a CUDA GPU and
               weights downloaded beforehand, see ml/models/README.md)
    auto       diffusers when it is usable, otherwise mock

A generator never decides anything and never receives who is in the media.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol


class GeneratorUnavailable(RuntimeError):
    """The generator cannot run right now (service down, model missing, bad output)."""


@dataclass
class GeneratedImage:
    png: bytes
    generator: str  # name and version, recorded in the Shield manifest
    simulated: bool  # True for the mock: the UI and manifest say so


class GeneratorAdapter(Protocol):
    name: str

    def available(self) -> bool: ...

    def generate(self, prompt: str, image: Optional[bytes]) -> GeneratedImage: ...
