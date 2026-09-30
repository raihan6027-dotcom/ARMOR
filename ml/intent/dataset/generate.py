"""Generate the Intent AI dataset from templates, with a frozen stratified split.

    python ml/intent/dataset/generate.py            # writes intent_dataset.csv + paraphrase.csv
    python ml/intent/dataset/generate.py --check    # verify the committed files are unchanged

Schema (CSV, UTF-8): id, prompt, bahasa, media, intent, sumber, diperiksa_oleh, split

* 350 prompts per class x 10 classes = 3,500, balanced over language and media.
* split: 70/15/15 train/val/test, stratified by intent, fixed seed. The split is
  frozen: rows keep their split forever, and splits.json stores a hash of the test
  set so Fase 6b retraining can prove the test set never changed.
* diperiksa_oleh is empty: every row must be reviewed by a team member before the
  final training run (see docs/intent-labeling-guide.md).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import sys
from itertools import product
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from paraphrase import PARAPHRASES  # noqa: E402
from templates import ACTIONS, LANGS, MEDIA, SELF_CLASSES, SUBJECTS, TAILS, VERBS  # noqa: E402

SEED = 20260930
PER_CLASS = 350
FIELDS = ["id", "prompt", "bahasa", "media", "intent", "sumber", "diperiksa_oleh", "split"]
DATASET = HERE / "intent_dataset.csv"
PARAPHRASE = HERE / "paraphrase.csv"
SPLITS = HERE / "splits.json"


def _subjects(lang: str, media: str, intent: str) -> list[str]:
    voice_words = ("suara", "voice")
    visual_words = ("foto", "photo", "wajah", "face", "video")
    pool = list(SUBJECTS[lang]["other"])
    if intent in SELF_CLASSES:
        pool = SUBJECTS[lang]["self"] * 2 + pool  # mostly about the requester
    if media == "AUDIO":
        pool = [s for s in pool if not any(w in s for w in visual_words)]
    else:
        pool = [s for s in pool if not any(w in s for w in voice_words)]
    return pool


def _actions(intent: str, lang: str, media: str) -> list[str]:
    table = ACTIONS[intent][lang]
    if media == "AUDIO":
        return table.get("AUDIO") or table["any"]
    return table["any"] + table.get(media, [])


def candidates(intent: str, lang: str, media: str) -> list[str]:
    out = []
    for verb, subject, action, tail in product(
        VERBS[lang][media],
        _subjects(lang, media, intent),
        _actions(intent, lang, media),
        TAILS[lang],
    ):
        text = f"{verb} {action.format(s=subject)}{tail}".strip()
        out.append(text[0].upper() + text[1:])
    return sorted(set(out))


def build(seed: int = SEED) -> list[dict]:
    rng = random.Random(seed)
    rows = []
    cells = list(product(LANGS, MEDIA))
    for intent in ACTIONS:
        per_cell = [PER_CLASS // len(cells)] * len(cells)
        for k in range(PER_CLASS - sum(per_cell)):
            per_cell[k] += 1
        chosen = []
        for (lang, media), n in zip(cells, per_cell, strict=True):
            pool = candidates(intent, lang, media)
            rng.shuffle(pool)
            chosen += [(lang, media, p) for p in pool[:n]]
        for lang, media, prompt in chosen:
            rows.append(
                {
                    "prompt": prompt,
                    "bahasa": lang,
                    "media": media,
                    "intent": intent,
                    "sumber": "template",
                    "diperiksa_oleh": "",
                }
            )
    # Stratified 70/15/15 split per intent.
    for intent in ACTIONS:
        idx = [i for i, r in enumerate(rows) if r["intent"] == intent]
        rng.shuffle(idx)
        n = len(idx)
        n_train, n_val = round(n * 0.70), round(n * 0.15)
        for pos, i in enumerate(idx):
            rows[i]["split"] = (
                "train" if pos < n_train else "val" if pos < n_train + n_val else "test"
            )
    rng.shuffle(rows)
    for k, r in enumerate(rows, start=1):
        r["id"] = f"INT-{k:05d}"
    return rows


def build_paraphrases() -> list[dict]:
    return [
        {
            "id": f"PAR-{k:04d}",
            "prompt": prompt,
            "bahasa": lang,
            "media": media,
            "intent": intent,
            "sumber": "parafrase-manual",
            "diperiksa_oleh": "",
            "split": "robustness",
        }
        for k, (intent, lang, media, prompt) in enumerate(PARAPHRASES, start=1)
    ]


def split_hash(rows: list[dict]) -> str:
    test = sorted((r["id"], r["prompt"], r["intent"]) for r in rows if r["split"] == "test")
    return hashlib.sha256(json.dumps(test, ensure_ascii=False).encode()).hexdigest()


def write(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def read(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--check", action="store_true", help="fail if committed files differ")
    args = ap.parse_args()

    rows, para = build(), build_paraphrases()
    if args.check:
        if not SPLITS.exists():
            print("splits.json tidak ada", file=sys.stderr)
            return 1
        frozen = json.loads(SPLITS.read_text(encoding="utf-8"))
        current = split_hash(read(DATASET))
        if current != frozen["test_sha256"]:
            print("Set uji berubah! Split beku dilanggar.", file=sys.stderr)
            return 1
        print("Set uji cocok dengan splits.json.")
        return 0

    if DATASET.exists():
        existing = read(DATASET)
        reviewed = {r["id"]: r["diperiksa_oleh"] for r in existing if r["diperiksa_oleh"]}
        if reviewed:
            print(
                f"{len(reviewed)} baris sudah diperiksa. Tidak menimpa dataset; "
                "ubah CSV secara manual.",
                file=sys.stderr,
            )
            return 1
    write(DATASET, rows)
    write(PARAPHRASE, para)
    counts = {s: sum(r["split"] == s for r in rows) for s in ("train", "val", "test")}
    SPLITS.write_text(
        json.dumps(
            {"seed": SEED, "counts": counts, "test_sha256": split_hash(rows)},
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"{len(rows)} prompt ({counts}) + {len(para)} parafrase -> {DATASET.parent}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
