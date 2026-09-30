"""Face AI verification evaluation: TAR at FAR 1% / 0.1%, EER, ROC, threshold.

Real run (after embed.py):

    python ml/face_eval/evaluate.py

writes docs/eval/face.md (numbers from real volunteer data only) and
docs/eval/face_roc.png.

Smoke run on SYNTHETIC embeddings, only to check that the code works:

    python ml/face_eval/evaluate.py --synthetic

writes docs/eval/synthetic/face-smoke.md. Those numbers are not results and must
never be copied into docs/eval/face.md or docs/eval/RINGKASAN.md.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))

from metrics import eer, enrollment_scores, pair_scores, recommend, roc, tar_at_far  # noqa: E402


def synthetic_dataset(persons: int = 30, photos: int = 8, noise: float = 0.9, seed: int = 7):
    """Clusters around random unit vectors: a stand-in with no real faces."""
    rng = np.random.default_rng(seed)
    centers = rng.standard_normal((persons, 512))
    centers /= np.linalg.norm(centers, axis=1, keepdims=True)
    emb, meta = [], []
    for p in range(persons):
        for k in range(photos):
            v = centers[p] + noise * rng.standard_normal(512) / np.sqrt(512)
            emb.append(v / np.linalg.norm(v))
            meta.append({"person": f"S{p:02d}", "split": "enroll" if k < 3 else "probe"})
    return np.stack(emb), meta


def load(path: Path):
    data = np.load(path)
    return data["embeddings"], json.loads(str(data["meta"]))


def evaluate(emb: np.ndarray, meta: list[dict]) -> dict:
    labels = [m["person"] for m in meta]
    g_pairs, i_pairs = pair_scores(emb, labels)
    curve_pairs = roc(g_pairs, i_pairs)

    enroll = {}
    for vec, m in zip(emb, meta, strict=True):
        if m["split"] == "enroll":
            enroll.setdefault(m["person"], []).append(vec)
    enroll = {k: np.stack(v) for k, v in enroll.items()}
    probe_idx = [i for i, m in enumerate(meta) if m["split"] == "probe" and m["person"] in enroll]
    g_tpl, i_tpl = enrollment_scores(enroll, emb[probe_idx], [labels[i] for i in probe_idx])
    curve_tpl = roc(g_tpl, i_tpl)

    out = {"persons": len(set(labels)), "photos": len(labels), "protocols": {}}
    for name, (g, i, curve) in {
        "pairs": (g_pairs, i_pairs, curve_pairs),
        "template": (g_tpl, i_tpl, curve_tpl),
    }.items():
        tar1, t1 = tar_at_far(curve, 0.01)
        tar01, t01 = tar_at_far(curve, 0.001)
        e, te = eer(curve)
        out["protocols"][name] = {
            "genuine": len(g),
            "impostor": len(i),
            "tar_far_1": tar1,
            "thr_far_1": t1,
            "tar_far_01": tar01,
            "thr_far_01": t01,
            "eer": e,
            "thr_eer": te,
            "curve": curve,
        }
    rec = recommend(curve_tpl)
    out["recommendation"] = rec
    return out


def plot(result: dict, path: Path, title: str) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(5, 4), dpi=120)
    for name, p in result["protocols"].items():
        c = p["curve"]
        ax.plot(np.clip(c.far, 1e-5, 1), c.tar, label=f"{name} (EER {p['eer']:.3f})")
    ax.set_xscale("log")
    ax.set_xlabel("FAR")
    ax.set_ylabel("TAR")
    ax.set_title(title)
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(loc="lower right")
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)


def report(result: dict, synthetic: bool, png_name: str) -> str:
    rec = result["recommendation"]
    head = (
        "# Evaluasi Face AI (SINTETIS, BUKAN HASIL)\n\n"
        "Dijalankan dengan embedding SINTETIS hanya untuk memastikan kode evaluasi "
        "berjalan. Angka di bawah TIDAK BOLEH dipakai di proposal atau RINGKASAN.md.\n"
        if synthetic
        else "# Evaluasi Face AI\n\nDihitung dari foto relawan yang memberi persetujuan "
        "(docs/consent-form-relawan.md) dengan pipeline yang sama dengan backend.\n"
    )
    lines = [
        head,
        f"- Tanggal: {date.today().isoformat()}",
        f"- Relawan: {result['persons']}, foto: {result['photos']}",
        (
            "- Cara mereproduksi: `python ml/face_eval/evaluate.py --synthetic`"
            if synthetic
            else "- Cara mereproduksi: `python ml/face_eval/embed.py` lalu "
            "`python ml/face_eval/evaluate.py`"
        ),
        "",
        "| Protokol | Pasangan asli | Pasangan asing | TAR @ FAR 1% | Ambang | "
        "TAR @ FAR 0,1% | Ambang | EER |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for name, p in result["protocols"].items():
        lines.append(
            f"| {name} | {p['genuine']} | {p['impostor']} | {p['tar_far_1']:.3f} | "
            f"{p['thr_far_1']:.3f} | {p['tar_far_01']:.3f} | {p['thr_far_01']:.3f} | "
            f"{p['eer']:.3f} |"
        )
    lines += [
        "",
        "Protokol `pairs`: semua pasangan foto. Protokol `template`: foto probe dibandingkan "
        "dengan rata-rata 3 foto enrollment tiap orang, sama seperti gateway.",
        "",
        f"![ROC]({png_name})",
        "",
        "## Rekomendasi konfigurasi",
        "",
        f"- `FACE_MATCH_THRESHOLD={rec.threshold}`",
        f"- `FACE_GRAY_MARGIN={rec.gray_margin}`",
        f"- Dasar: {rec.rationale}",
    ]
    if synthetic:
        lines.append("- Rekomendasi di atas dari data SINTETIS: jangan dipakai.")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--synthetic", action="store_true")
    ap.add_argument("--embeddings", type=Path, default=HERE / "data" / "embeddings.npz")
    args = ap.parse_args()

    if args.synthetic:
        emb, meta = synthetic_dataset()
        out_dir, name = REPO / "docs" / "eval" / "synthetic", "face-smoke"
    else:
        if not args.embeddings.exists():
            print(
                "Belum ada embedding relawan. Jalankan embed.py dulu (lihat README.md).",
                file=sys.stderr,
            )
            return 2
        emb, meta = load(args.embeddings)
        out_dir, name = REPO / "docs" / "eval", "face"

    result = evaluate(emb, meta)
    png = out_dir / f"{name}_roc.png"
    plot(result, png, "Face AI ROC" + (" (SINTETIS)" if args.synthetic else ""))
    md = out_dir / f"{name}.md"
    md.write_text(report(result, args.synthetic, png.name), encoding="utf-8")
    print(f"Laporan: {md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
