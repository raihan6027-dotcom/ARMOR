"""SIMULATED generative AI service for the offline ARMOR demo.

Run:  uvicorn armor_generator_mock.service:app --app-dir generator_mock --port 8200

The ARMOR backend calls POST /generate only after its policy engine returned
ALLOW, then passes the result through the Output Guard and ARMOR Shield. This
service never decides anything and keeps nothing: inputs and outputs live only in
memory for the duration of the call.

Test mode (for the Output Guard demo, CLAUDE.md Lampiran A skenario 15):
  GENERATOR_TEST_MODE=inject_face
  GENERATOR_INJECT_DIR=<folder with one or more face photos>   (never committed)
Every output then also contains a face from that folder. A request may instead
carry `test_inject_image` (base64), accepted only while test mode is on.
"""

from __future__ import annotations

import base64
import binascii
import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from armor_generator_mock.transforms import (
    GENERATOR_NAME,
    GENERATOR_VERSION,
    SIMULATION_NOTE,
    GeneratorInputError,
    generate,
)

MAX_INPUT_BYTES = 10 * 1024 * 1024
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}

app = FastAPI(
    title="ARMOR generator tiruan (SIMULASI)",
    version=GENERATOR_VERSION,
    description="Simulasi AI generatif untuk demo ARMOR. Bukan model generatif.",
)


class GenerateIn(BaseModel):
    prompt: str = Field(min_length=1, max_length=2000)
    image: Optional[str] = None  # base64; absent for text-only requests
    test_inject_image: Optional[str] = None  # base64; only honoured in test mode


class GenerateOut(BaseModel):
    image: str  # base64 PNG
    generator: str
    version: str
    simulated: bool = True
    note: str = SIMULATION_NOTE
    style: str
    test_mode: Optional[str] = None


def test_mode() -> str:
    return os.environ.get("GENERATOR_TEST_MODE", "").strip()


def _b64(value: str, field: str) -> bytes:
    try:
        data = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(422, f"{field} is not valid base64") from exc
    if len(data) > MAX_INPUT_BYTES:
        raise HTTPException(413, f"{field} is too large")
    return data


def _inject_from_dir() -> Optional[bytes]:
    folder = os.environ.get("GENERATOR_INJECT_DIR", "").strip()
    if not folder:
        return None
    files = sorted(p for p in Path(folder).iterdir() if p.suffix.lower() in IMAGE_SUFFIXES)
    return files[0].read_bytes() if files else None


@app.get("/health")
def health():
    return {
        "status": "ok",
        "generator": GENERATOR_NAME,
        "version": GENERATOR_VERSION,
        "simulated": True,
        "test_mode": test_mode() or None,
    }


@app.post("/generate", response_model=GenerateOut)
def generate_endpoint(body: GenerateIn):
    image = _b64(body.image, "image") if body.image else None
    inject = None
    mode = test_mode()
    if body.test_inject_image:
        if mode != "inject_face":
            raise HTTPException(403, "test_inject_image is only accepted in test mode")
        inject = _b64(body.test_inject_image, "test_inject_image")
    elif mode == "inject_face":
        inject = _inject_from_dir()
        if inject is None:
            raise HTTPException(500, "GENERATOR_INJECT_DIR has no image")
    try:
        out = generate(body.prompt, image, inject)
    except GeneratorInputError as exc:
        raise HTTPException(422, str(exc)) from exc
    return GenerateOut(
        image=base64.b64encode(out.png).decode(),
        generator=GENERATOR_NAME,
        version=GENERATOR_VERSION,
        style=out.style,
        test_mode=mode or None,
    )
