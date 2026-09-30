"""Embed volunteer photos with the SAME pipeline the backend uses (app.ai.face).

CLAUDE.md bagian 12: enrollment and inference must use identical preprocessing,
so this script imports the backend's FaceAI instead of re-implementing it.

Input layout (never committed, see README.md):

    ml/face_eval/data/relawan/<KODE>/enroll/*.jpg   3 photos: straight, left, right
    ml/face_eval/data/relawan/<KODE>/probe/*.jpg    other photos of the same person

Output: ml/face_eval/data/embeddings.npz (biometric data: also never committed).

    python ml/face_eval/embed.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "backend"))

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def _images(folder: Path) -> list[Path]:
    if not folder.exists():
        return []
    return sorted(p for p in folder.iterdir() if p.suffix.lower() in IMAGE_EXT)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--data", type=Path, default=HERE / "data" / "relawan")
    ap.add_argument("--out", type=Path, default=HERE / "data" / "embeddings.npz")
    args = ap.parse_args()

    from app.ai.face import FaceAI

    ai = FaceAI()
    if not ai.available:
        print(f"Model wajah tidak tersedia: {ai.init_error}", file=sys.stderr)
        return 2
    if not args.data.exists():
        print(f"Folder data tidak ada: {args.data}. Lihat ml/face_eval/README.md.", file=sys.stderr)
        return 2

    rows, skipped = [], []
    for person in sorted(p for p in args.data.iterdir() if p.is_dir()):
        for split in ("enroll", "probe"):
            for img in _images(person / split):
                faces = ai.analyze(img.read_bytes())
                if not faces:
                    skipped.append({"file": str(img.relative_to(args.data)), "why": "no_face"})
                    continue
                f = faces[0]
                rows.append(
                    {
                        "person": person.name,
                        "split": split,
                        "file": str(img.relative_to(args.data)),
                        "embedding": f.embedding,
                        "quality_ok": f.quality_ok,
                        "issues": ",".join(f.issues),
                        "yaw": f.yaw,
                    }
                )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        args.out,
        embeddings=np.stack([r["embedding"] for r in rows]) if rows else np.zeros((0, 512)),
        meta=json.dumps([{k: v for k, v in r.items() if k != "embedding"} for r in rows]),
        skipped=json.dumps(skipped),
    )
    persons = len({r["person"] for r in rows})
    print(f"{len(rows)} foto dari {persons} relawan -> {args.out}; dilewati: {len(skipped)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
