"""The generator is a simulation: check it is marked as one, picks styles from the
prompt, never fails silently on bad input, and that test mode really puts the
injected face pixels into the output."""

import base64
import io

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from armor_generator_mock import service
from armor_generator_mock.transforms import SIMULATION_NOTE, generate, style_for


def png(color=(200, 120, 80), size=(64, 48)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


def open_png(data: bytes) -> Image.Image:
    img = Image.open(io.BytesIO(data))
    img.load()
    return img


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.delenv("GENERATOR_TEST_MODE", raising=False)
    monkeypatch.delenv("GENERATOR_INJECT_DIR", raising=False)
    return TestClient(service.app)


@pytest.mark.parametrize(
    ("prompt", "style"),
    [
        ("Buatkan avatar kartun dari wajah saya.", "cartoon"),
        ("Buat karikatur superhero dari foto ini.", "cartoon"),
        ("Cerahkan foto saya ini.", "brighten"),
        ("Make a pencil sketch of this photo", "sketch"),
        ("Jadikan hitam putih", "mono"),
        ("Tambahkan latar pantai", "stylize"),
    ],
)
def test_style_from_prompt(prompt, style):
    assert style_for(prompt) == style


def test_output_is_marked_as_simulation_and_resized():
    out = generate("Buat karikatur superhero dari foto ini.", png(size=(8, 8)))
    img = open_png(out.png)
    assert img.text["armor-generator"] == SIMULATION_NOTE
    assert min(img.size) >= 256
    assert out.style == "cartoon" and not out.injected


def test_large_input_is_capped():
    out = generate("Cerahkan", png(size=(3000, 1500)))
    assert max(open_png(out.png).size) == 1024


def test_text_only_is_deterministic_per_prompt():
    a = generate("Pemandangan gunung saat pagi")
    b = generate("Pemandangan gunung saat pagi")
    c = generate("Kota di malam hari")
    assert a.png == b.png and a.png != c.png
    assert open_png(a.png).size == (512, 512)


def test_inject_face_pastes_the_face_pixels():
    face = png(color=(255, 0, 255), size=(40, 40))
    out = open_png(generate("Cerahkan foto ini", png(color=(10, 10, 10)), face).png)
    pixels = np.asarray(out.convert("RGB")).reshape(-1, 3)
    magenta = np.all(pixels == (255, 0, 255), axis=1).mean()
    assert magenta > 0.05
    assert "+inject_face" in out.text["armor-generator-style"]


def test_service_generate_and_health(client):
    r = client.post(
        "/generate",
        json={"prompt": "Buatkan avatar kartun", "image": base64.b64encode(png()).decode()},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["simulated"] is True and body["style"] == "cartoon"
    assert open_png(base64.b64decode(body["image"])).format == "PNG"
    assert client.get("/health").json()["simulated"] is True


def test_service_rejects_bad_input(client):
    assert client.post("/generate", json={"prompt": "x", "image": "%%%"}).status_code == 422
    junk = base64.b64encode(b"not an image").decode()
    assert client.post("/generate", json={"prompt": "x", "image": junk}).status_code == 422


def test_inject_request_refused_outside_test_mode(client):
    face = base64.b64encode(png()).decode()
    r = client.post("/generate", json={"prompt": "x", "test_inject_image": face})
    assert r.status_code == 403


def test_test_mode_injects_from_folder(client, monkeypatch, tmp_path):
    (tmp_path / "wajah.png").write_bytes(png(color=(255, 0, 255), size=(40, 40)))
    monkeypatch.setenv("GENERATOR_TEST_MODE", "inject_face")
    monkeypatch.setenv("GENERATOR_INJECT_DIR", str(tmp_path))
    body = client.post("/generate", json={"prompt": "Pemandangan"}).json()
    assert body["test_mode"] == "inject_face"
    img = open_png(base64.b64decode(body["image"]))
    assert "+inject_face" in img.text["armor-generator-style"]


def test_test_mode_without_faces_fails_loudly(client, monkeypatch, tmp_path):
    monkeypatch.setenv("GENERATOR_TEST_MODE", "inject_face")
    monkeypatch.setenv("GENERATOR_INJECT_DIR", str(tmp_path))
    assert client.post("/generate", json={"prompt": "Pemandangan"}).status_code == 500
