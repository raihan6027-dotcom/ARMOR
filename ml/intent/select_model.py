"""Pick the Intent AI model the backend loads, and write docs/eval/intent.md.

    python ml/intent/select_model.py

Candidates: ml/models/intent/baseline_report.json and indobert_report.json (if
present and its model files exist). Selection, in order:
1. lower harmful leak rate on the paraphrase set (harmful prompts classified as a
   permissive class are the misses that can be ALLOWed),
2. higher mean recall of the harmful classes on the paraphrase set,
3. higher macro F1 on the paraphrase set,
4. higher macro F1 on the frozen test set.
The paraphrase set comes first because the template test set is too easy to
separate the models (see docs/eval/intent.md).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from common import HARMFUL, LABELS, MODEL_DIR, REPO  # noqa: E402

CANDIDATES = {
    "baseline": {
        "report": "baseline_report.json",
        "kind": "sklearn",
        "file": "intent_tfidf_lr.joblib",
    },
    "indobert": {"report": "indobert_report.json", "kind": "transformers", "file": "indobert"},
}


def _key(rep: dict) -> tuple:
    p, t = rep["paraphrase"], rep["test"]
    leak = p.get("harmful_leak_rate")
    return (
        -(leak if leak is not None else 1.0),
        p["harmful_recall_mean"],
        p["macro_f1"],
        t["macro_f1"],
    )


def load_candidates() -> dict[str, dict]:
    found = {}
    for name, c in CANDIDATES.items():
        rpath, mpath = MODEL_DIR / c["report"], MODEL_DIR / c["file"]
        if rpath.exists():
            found[name] = {
                **c,
                "report": json.loads(rpath.read_text(encoding="utf-8")),
                "model_present": mpath.exists(),
            }
    return found


def _fmt(v) -> str:
    return "-" if v is None else f"{v:.3f}"


def write_doc(found: dict[str, dict], chosen: str | None) -> Path:
    lines = ["# Evaluasi Intent AI", ""]
    experimental = any(c["report"].get("experiment_unreviewed_rows") for c in found.values())
    if experimental:
        lines += [
            "**Status: EKSPERIMEN.** Dataset belum diperiksa manusia (kolom `diperiksa_oleh` masih "
            "kosong). Angka di bawah hanya menunjukkan kondisi sistem saat ini, belum hasil final, dan "
            "tidak boleh masuk `docs/eval/RINGKASAN.md` sampai training diulang dengan dataset yang "
            "sudah diperiksa.",
            "",
        ]
    missing = [n for n in CANDIDATES if n not in found]
    for name in missing:
        lines += [
            f"- `{name}`: belum dijalankan"
            + (" (butuh GPU, lihat `ml/intent/train_indobert.py`)." if name == "indobert" else "."),
            "",
        ]
    lines += [
        "Cara mereproduksi: `python ml/intent/dataset/generate.py --check`, lalu "
        "`python ml/intent/train_baseline.py` (dan `train_indobert.py` di GPU), lalu "
        "`python ml/intent/select_model.py`.",
        "",
        "## Ringkasan",
        "",
        "| Model | Versi | Ambang UNCERTAIN | Uji: macro F1 | Uji: recall berbahaya | "
        "Parafrase: macro F1 | Parafrase: recall berbahaya | Parafrase: tingkat lolos |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for name, c in found.items():
        r = c["report"]
        lines.append(
            f"| {name}{' (dipakai)' if name == chosen else ''} | `{r['model_version']}` | {r['threshold']:.2f} | "
            f"{_fmt(r['test']['macro_f1'])} | {_fmt(r['test']['harmful_recall_mean'])} | "
            f"{_fmt(r['paraphrase']['macro_f1'])} | {_fmt(r['paraphrase']['harmful_recall_mean'])} | "
            f"{_fmt(r['paraphrase'].get('harmful_leak_rate'))} |"
        )
    lines += [
        "",
        "- **Set uji**: 15% dataset template yang dibekukan (`ml/intent/dataset/splits.json`).",
        "- **Set parafrase**: prompt tulisan tangan yang sengaja menghindari kata-kata template "
        "(eufemisme, parafrase). Tidak pernah dipakai untuk training.",
        "- **Tingkat lolos**: bagian prompt berbahaya yang diprediksi sebagai kelas permisif. Prompt "
        "berbahaya yang diprediksi UNCERTAIN tidak dihitung lolos, karena policy engine menjadikannya "
        "REVIEW (gagal aman).",
        "",
    ]
    for name, c in found.items():
        r = c["report"]
        lines += [
            f"## {name}: per kelas (set uji dan parafrase)",
            "",
            "| Kelas | F1 uji | F1 parafrase |",
            "| --- | --- | --- |",
        ]
        lines += [
            f"| {lbl} | {_fmt(r['test']['f1_per_class'][lbl])} | {_fmt(r['paraphrase']['f1_per_class'][lbl])} |"
            for lbl in LABELS
        ]
        lines += [
            "",
            "Recall kelas berbahaya pada parafrase: "
            + ", ".join(f"{lbl} {_fmt(r['paraphrase']['harmful_recall'][lbl])}" for lbl in HARMFUL)
            + ".",
        ]
        png = REPO / "docs" / "eval" / f"intent_confusion_{name}.png"
        if png.exists():
            lines += ["", f"![Confusion matrix {name}]({png.name})"]
        lines.append("")
    lines += [
        "## Catatan jujur",
        "",
        "- Skor sempurna di set uji template tidak berarti model sempurna: set uji dibuat dari "
        "template yang sama dengan data latih, sehingga model cukup menghafal pola kalimat. Set "
        "parafrase adalah ukuran yang lebih jujur.",
        "- Ambang UNCERTAIN dipilih dari data validasi template yang terlalu mudah, sehingga cenderung "
        "rendah. Pilih ulang setelah dataset diperkaya dengan prompt tulisan tangan tim.",
        "- Perbaikan yang disarankan: tim menambah prompt alami (sumber `manual`) terutama untuk "
        "eufemisme kelas berbahaya, lalu latih ulang. Jangan menyalin prompt dari set parafrase ke "
        "data latih, karena itu membuat set ketahanan tidak lagi jujur.",
    ]
    out = REPO / "docs" / "eval" / "intent.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def main() -> int:
    found = load_candidates()
    usable = {n: c for n, c in found.items() if c["model_present"]}
    chosen = max(usable, key=lambda n: _key(usable[n]["report"])) if usable else None
    if chosen:
        c, r = usable[chosen], usable[chosen]["report"]
        (MODEL_DIR / "active.json").write_text(
            json.dumps(
                {
                    "kind": c["kind"],
                    "file": c["file"],
                    "model_version": r["model_version"],
                    "threshold": r["threshold"],
                    "labels": LABELS,
                    "experiment": bool(r.get("experiment_unreviewed_rows")),
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    doc = write_doc(found, chosen)
    print(
        f"Model dipakai: {chosen or '(tidak ada, backend memakai fallback keyword)'}; laporan: {doc}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
