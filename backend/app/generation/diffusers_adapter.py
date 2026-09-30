"""Optional adapter for a real local generative model (Stable Diffusion via diffusers).

Active only when torch and diffusers are installed, a CUDA GPU is present, and the
weights were downloaded beforehand into GENERATOR_MODEL_DIR (a diffusers folder
with model_index.json). It never downloads anything at run time
(local_files_only), so the demo stays offline. Licence of the chosen checkpoint
must be recorded in docs/TECH_LIST.md.

Image requests use img2img (the checked photo is the starting point); text-only
requests use text2img from the same weights.
"""

from __future__ import annotations

import importlib.util
import io
from pathlib import Path
from typing import Any, Optional

from app.generation.adapter import GeneratedImage, GeneratorUnavailable

IMG2IMG_STRENGTH = 0.55
STEPS = 25
SIZE = 512


def _installed(module: str) -> bool:
    return importlib.util.find_spec(module) is not None


class DiffusersAdapter:
    name = "diffusers"

    def __init__(self, model_dir: str):
        self.model_dir = Path(model_dir)
        self._img2img: Any = None
        self._txt2img: Any = None

    def available(self) -> bool:
        if not (self.model_dir / "model_index.json").is_file():
            return False
        if not (_installed("torch") and _installed("diffusers")):
            return False
        import torch

        return bool(torch.cuda.is_available())

    def _load(self) -> None:
        if self._img2img is not None:
            return
        if not self.available():
            raise GeneratorUnavailable("local diffusers model not available")
        import torch
        from diffusers import AutoPipelineForImage2Image, AutoPipelineForText2Image

        txt = AutoPipelineForText2Image.from_pretrained(
            str(self.model_dir), torch_dtype=torch.float16, local_files_only=True
        ).to("cuda")
        self._txt2img = txt
        self._img2img = AutoPipelineForImage2Image.from_pipe(txt)

    def generate(self, prompt: str, image: Optional[bytes]) -> GeneratedImage:
        self._load()
        from PIL import Image

        try:
            if image is None:
                out = self._txt2img(prompt, num_inference_steps=STEPS, height=SIZE, width=SIZE)
            else:
                init = Image.open(io.BytesIO(image)).convert("RGB").resize((SIZE, SIZE))
                out = self._img2img(
                    prompt, image=init, strength=IMG2IMG_STRENGTH, num_inference_steps=STEPS
                )
        except Exception as exc:  # noqa: BLE001 - any model failure means no output
            raise GeneratorUnavailable(f"local model failed: {exc}") from exc
        buf = io.BytesIO()
        out.images[0].save(buf, format="PNG")
        return GeneratedImage(
            png=buf.getvalue(), generator=f"diffusers {self.model_dir.name}", simulated=False
        )
