"""Adapter for the SIMULATED generator in generator_mock/ (an HTTP service)."""

from __future__ import annotations

import base64
import binascii
from typing import Optional

import httpx

from app.generation.adapter import GeneratedImage, GeneratorUnavailable


class MockGeneratorAdapter:
    name = "mock"

    def __init__(self, base_url: str, timeout_s: float, client: Optional[httpx.Client] = None):
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s
        # Tests inject a TestClient bound to the generator_mock app.
        self._client = client

    def _http(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(base_url=self.base_url, timeout=self.timeout_s)
        return self._client

    def available(self) -> bool:
        try:
            return self._http().get("/health").status_code == 200
        except httpx.HTTPError:
            return False

    def generate(self, prompt: str, image: Optional[bytes]) -> GeneratedImage:
        body = {"prompt": prompt}
        if image is not None:
            body["image"] = base64.b64encode(image).decode()
        try:
            r = self._http().post("/generate", json=body)
        except httpx.HTTPError as exc:
            raise GeneratorUnavailable(f"generator_mock unreachable: {exc}") from exc
        if r.status_code != 200:
            raise GeneratorUnavailable(f"generator_mock returned {r.status_code}")
        data = r.json()
        try:
            png = base64.b64decode(data["image"], validate=True)
        except (KeyError, binascii.Error, ValueError) as exc:
            raise GeneratorUnavailable("generator_mock returned no image") from exc
        name = f"{data.get('generator', 'armor-generator-mock')} {data.get('version', '')}"
        return GeneratedImage(
            png=png,
            generator=name.strip(),
            simulated=bool(data.get("simulated", True)),
        )
