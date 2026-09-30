"""SIMULATED generative AI: simple Pillow image operations chosen from the prompt.

Nothing here is a generative model. It exists so the ARMOR pipeline after an
ALLOW decision (generator -> Output Guard -> ARMOR Shield) can be demonstrated
offline on a laptop without a GPU. Every output is marked as a simulation in its
PNG metadata.

Test mode `inject_face` pastes a given image (for example a volunteer's face
photo) into the output, so the Output Guard can be shown catching a registered
face that the prompt never asked for (CLAUDE.md Lampiran A, skenario 15).
"""

from __future__ import annotations

import hashlib
import io
import re
from dataclasses import dataclass
from typing import Optional

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps
from PIL.PngImagePlugin import PngInfo

GENERATOR_NAME = "armor-generator-mock"
GENERATOR_VERSION = "mock-1"
SIMULATION_NOTE = "SIMULASI: bukan model AI generatif"
MIN_SIDE = 256
MAX_SIDE = 1024
TEXT_SIZE = 512

# Style chosen from the prompt (Indonesian and English keywords), first match wins.
STYLES: list[tuple[str, re.Pattern[str]]] = [
    ("sketch", re.compile(r"\b(sketsa|sketch|pensil|pencil|gambar garis)\b", re.I)),
    ("mono", re.compile(r"\b(hitam putih|black and white|monokrom|grayscale)\b", re.I)),
    (
        "cartoon",
        re.compile(
            r"\b(kartun|cartoon|avatar|karikatur|caricature|anime|komik|comic|superhero|pahlawan)\b",
            re.I,
        ),
    ),
    (
        "brighten",
        re.compile(r"\b(cerah\w*|terang\w*|brighten|pencahayaan|lighting|perbaiki)\b", re.I),
    ),
]


class GeneratorInputError(ValueError):
    """The input image cannot be decoded."""


@dataclass
class Output:
    png: bytes
    style: str
    injected: bool


def style_for(prompt: str) -> str:
    for name, pattern in STYLES:
        if pattern.search(prompt):
            return name
    return "stylize"


def _decode(data: bytes) -> Image.Image:
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception as exc:  # noqa: BLE001
        raise GeneratorInputError("image cannot be decoded") from exc
    return ImageOps.exif_transpose(img).convert("RGB")


def _fit(img: Image.Image) -> Image.Image:
    """Scale so the short side is at least MIN_SIDE and the long side at most MAX_SIDE."""
    w, h = img.size
    scale = max(MIN_SIDE / min(w, h), 1.0)
    if max(w, h) * scale > MAX_SIDE:
        scale = MAX_SIDE / max(w, h)
    if abs(scale - 1.0) < 1e-6:
        return img
    return img.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.LANCZOS)


def _cartoon(img: Image.Image, vivid: bool) -> Image.Image:
    smooth = img.filter(ImageFilter.MedianFilter(5))
    flat = ImageOps.posterize(smooth, 3)
    if vivid:
        flat = ImageEnhance.Color(flat).enhance(1.6)
    edges = ImageOps.invert(smooth.convert("L").filter(ImageFilter.FIND_EDGES))
    edges = edges.point(lambda v: 0 if v < 200 else 255)
    return Image.composite(flat, Image.new("RGB", img.size, (20, 20, 30)), edges)


def _sketch(img: Image.Image) -> Image.Image:
    gray = img.convert("L")
    edges = ImageOps.invert(gray.filter(ImageFilter.FIND_EDGES))
    return ImageOps.autocontrast(edges).convert("RGB")


def transform(img: Image.Image, style: str, prompt: str) -> Image.Image:
    img = _fit(img)
    if style == "cartoon":
        return _cartoon(img, vivid=bool(re.search(r"superhero|pahlawan", prompt, re.I)))
    if style == "sketch":
        return _sketch(img)
    if style == "mono":
        return ImageOps.grayscale(img).convert("RGB")
    if style == "brighten":
        return ImageEnhance.Contrast(ImageEnhance.Brightness(img).enhance(1.25)).enhance(1.1)
    return ImageOps.posterize(ImageEnhance.Color(img).enhance(1.3), 5)


def from_text(prompt: str) -> Image.Image:
    """Text-only request: an abstract composition seeded by the prompt."""
    seed = hashlib.sha256(prompt.encode("utf-8")).digest()
    img = Image.new("RGB", (TEXT_SIZE, TEXT_SIZE))
    draw = ImageDraw.Draw(img)
    top, bottom = seed[0:3], seed[3:6]
    for y in range(TEXT_SIZE):
        t = y / (TEXT_SIZE - 1)
        draw.line(
            [(0, y), (TEXT_SIZE, y)],
            fill=tuple(round(a + (b - a) * t) for a, b in zip(top, bottom, strict=True)),
        )
    for i in range(6):
        b = seed[6 + i * 4 : 10 + i * 4]
        x, y, r = b[0] * 2, b[1] * 2, 20 + b[2] // 3
        color = (b[3], 255 - b[3], (b[0] + b[1]) % 256)
        if i % 2:
            draw.ellipse([x - r, y - r, x + r, y + r], fill=color)
        else:
            draw.rectangle([x - r, y - r // 2, x + r, y + r // 2], fill=color)
    return img


def inject(base: Image.Image, face: Image.Image) -> Image.Image:
    """Paste `face` (unchanged pixels, scaled) at the right side of `base`."""
    out = base.copy()
    target_w = max(64, out.width * 2 // 5)
    scale = min(target_w / face.width, (out.height * 4 // 5) / face.height)
    pasted = face.resize((max(1, round(face.width * scale)), max(1, round(face.height * scale))))
    x = out.width - pasted.width - out.width // 20
    y = (out.height - pasted.height) // 2
    out.paste(pasted, (max(0, x), max(0, y)))
    return out


def to_png(img: Image.Image, style: str, injected: bool) -> bytes:
    info = PngInfo()
    info.add_text("Software", f"{GENERATOR_NAME} {GENERATOR_VERSION}")
    info.add_text("armor-generator", SIMULATION_NOTE)
    info.add_text("armor-generator-style", style + (" +inject_face" if injected else ""))
    buf = io.BytesIO()
    img.save(buf, format="PNG", pnginfo=info)
    return buf.getvalue()


def generate(
    prompt: str, image: Optional[bytes] = None, inject_face: Optional[bytes] = None
) -> Output:
    if image is not None:
        style = style_for(prompt)
        img = transform(_decode(image), style, prompt)
    else:
        style = "text"
        img = from_text(prompt)
    if inject_face is not None:
        img = inject(img, _decode(inject_face))
    return Output(
        png=to_png(img, style, inject_face is not None), style=style, injected=bool(inject_face)
    )
