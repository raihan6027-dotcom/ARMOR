"""Enrollment attack evaluation: how many fake enrollments are refused?

Runs the backend's own enrollment defenses (identity_service.check_enrollment_captures
and duplicate_of) on three kinds of attack attempt, each a folder of 3 photos:

    ml/face_eval/data/serangan/layar/<percobaan>/*.jpg      face shown on a screen
    ml/face_eval/data/serangan/cetak/<percobaan>/*.jpg      printed photo
    ml/face_eval/data/serangan/terdaftar/<percobaan>/*.jpg  a volunteer who is already
                                                            enrolled, from another account

Registered faces are the volunteers' enrollment photos (embeddings.npz from embed.py).

    python ml/face_eval/attacks.py              # real data -> docs/eval/face-attacks.md
    python ml/face_eval/attacks.py --synthetic  # SINTETIS smoke run, not a result
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "backend"))

KINDS = {
    "layar": "Foto dari layar",
    "cetak": "Foto cetak",
    "terdaftar": "Wajah yang sudah terdaftar",
}


class _Registered:
    def __init__(self, name: str):
        self.identity_id = name


def run_attempt(images: list[bytes], registered: list[tuple[_Registered, np.ndarray]]) -> str:
    """'ACCEPTED' or the refusal code the backend would return."""
    from app.core.exceptions import ArmorError
    from app.services import identity_service

    try:
        mean = identity_service.check_enrollment_captures(images)
    except ArmorError as exc:
        return exc.code
    if identity_service.duplicate_of(mean, registered) is not None:
        return "FACE_ALREADY_REGISTERED"
    return "ACCEPTED"


def summarize(results: dict[str, list[str]]) -> list[dict]:
    rows = []
    for kind, codes in results.items():
        refused = [c for c in codes if c != "ACCEPTED"]
        rows.append(
            {
                "kind": kind,
                "attempts": len(codes),
                "refused": len(refused),
                "rate": (len(refused) / len(codes)) if codes else None,
                "reasons": dict(Counter(refused)),
            }
        )
    return rows


def report(rows: list[dict], synthetic: bool) -> str:
    head = (
        "# Uji serangan enrollment wajah (SINTETIS, BUKAN HASIL)\n\n"
        "Dijalankan dengan data SINTETIS hanya untuk memastikan kode berjalan. "
        "Angka di bawah TIDAK BOLEH dipakai di proposal atau RINGKASAN.md.\n"
        if synthetic
        else "# Uji serangan enrollment wajah\n\nSetiap percobaan adalah 3 foto yang dikirim "
        "ke pemeriksaan enrollment backend yang sama dengan aplikasi.\n"
    )
    lines = [
        head,
        f"- Tanggal: {date.today().isoformat()}",
        "- Cara mereproduksi: `python ml/face_eval/attacks.py"
        + (" --synthetic`" if synthetic else "`"),
        "",
        "| Serangan | Percobaan | Tertolak | Persentase tertolak | Alasan penolakan |",
        "| --- | --- | --- | --- | --- |",
    ]
    for r in rows:
        rate = "belum ada data" if r["rate"] is None else f"{r['rate']:.1%}"
        reasons = ", ".join(f"{k}: {v}" for k, v in sorted(r["reasons"].items())) or "-"
        lines.append(
            f"| {KINDS[r['kind']]} | {r['attempts']} | {r['refused']} | {rate} | {reasons} |"
        )
    return "\n".join(lines) + "\n"


# --- Synthetic smoke mode ----------------------------------------------------------


def _synthetic_setup():
    """Fake camera: bytes are JSON describing one face; no model, no real person."""
    from app.ai.face import DetectedFace, l2_normalize, quality_issues
    from app.services import identity_service

    rng = np.random.default_rng(3)
    people = {f"S{i:02d}": l2_normalize(rng.standard_normal(512)) for i in range(10)}

    def analyze(data: bytes):
        spec = json.loads(data)
        base = people[spec["who"]]
        v = l2_normalize(base + spec.get("noise", 0.2) * rng.standard_normal(512) / 20)
        return [
            DetectedFace(
                bbox=(0, 0, 160, 160),
                embedding=v,
                det_score=0.99,
                size_px=spec.get("size", 160),
                blur_var=spec.get("blur", 200),
                yaw=spec["yaw"],
                pitch=0.0,
                issues=quality_issues(spec.get("size", 160), spec.get("blur", 200), spec["yaw"], 0),
            )
        ]

    class FakeAI:
        pass

    fake = FakeAI()
    fake.analyze = analyze
    identity_service.face_ai = fake

    def shot(who, yaw, **kw):
        return json.dumps({"who": who, "yaw": yaw, **kw}).encode()

    registered = [(_Registered(n), v) for n, v in list(people.items())[:5]]
    attempts = {
        # A screen held still: same angle three times, slight moiré blur.
        "layar": [[shot("S07", 0, blur=90) for _ in range(3)] for _ in range(20)],
        # A printed photo: same angle, flat and blurry.
        "cetak": [[shot("S08", 1, blur=40) for _ in range(3)] for _ in range(20)],
        # A real, moving face that is already registered to someone else.
        "terdaftar": [[shot("S01", y) for y in (-15, 0, 15)] for _ in range(20)],
    }
    return registered, attempts


def _real_setup():
    data = HERE / "data"
    emb_path = data / "embeddings.npz"
    if not emb_path.exists():
        return None, None
    from app.ai.face import FaceAI
    from app.services import identity_service

    ai = FaceAI()
    if not ai.available:
        print(f"Model wajah tidak tersedia: {ai.init_error}", file=sys.stderr)
        return None, None
    identity_service.face_ai = ai

    npz = np.load(emb_path)
    meta = json.loads(str(npz["meta"]))
    templates: dict[str, list[np.ndarray]] = {}
    for vec, m in zip(npz["embeddings"], meta, strict=True):
        if m["split"] == "enroll":
            templates.setdefault(m["person"], []).append(vec)
    registered = [
        (_Registered(k), np.mean(v, axis=0) / np.linalg.norm(np.mean(v, axis=0)))
        for k, v in templates.items()
    ]
    attempts: dict[str, list[list[bytes]]] = {}
    for kind in KINDS:
        root = data / "serangan" / kind
        attempts[kind] = [
            [p.read_bytes() for p in sorted(folder.iterdir()) if p.is_file()][:3]
            for folder in (sorted(root.iterdir()) if root.exists() else [])
            if folder.is_dir()
        ]
    return registered, attempts


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--synthetic", action="store_true")
    args = ap.parse_args()

    registered, attempts = _synthetic_setup() if args.synthetic else _real_setup()
    if registered is None:
        print(
            "Butuh embeddings.npz (embed.py) dan folder data/serangan/. Lihat README.md.",
            file=sys.stderr,
        )
        return 2
    results = {kind: [run_attempt(a, registered) for a in atts] for kind, atts in attempts.items()}
    out = (
        REPO
        / "docs"
        / "eval"
        / ("synthetic/face-attacks-smoke.md" if args.synthetic else "face-attacks.md")
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report(summarize(results), args.synthetic), encoding="utf-8")
    print(f"Laporan: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
