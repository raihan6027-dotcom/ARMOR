"""Intent AI comparison model: fine-tune IndoBERT (needs a GPU; Colab or Kaggle).

Colab / Kaggle steps:

    !git clone <repo-url> armor && cd armor
    !pip install -q "transformers>=4.44" "torch>=2.3" scikit-learn matplotlib
    !python ml/intent/train_indobert.py --allow-unreviewed   # experiment
    # after the team reviewed every row:
    !python ml/intent/train_indobert.py

Then download ml/models/intent/indobert/ (model files) and
ml/models/intent/indobert_report.json to the demo laptop and run
`python ml/intent/select_model.py` to pick the better model.

Checkpoint: indobenchmark/indobert-base-p1 (IndoNLU). Check and record its
license in docs/TECH_LIST.md before using it in the submission.

The report has exactly the same format as train_baseline.py.
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, date, datetime
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from common import (  # noqa: E402
    DATASET,
    LABELS,
    MODEL_DIR,
    PARAPHRASE,
    REPO,
    apply_threshold,
    check_reviewed,
    choose_threshold,
    plot_confusion,
    read_rows,
    save_report,
    scores,
)

CHECKPOINT = "indobenchmark/indobert-base-p1"
OUT = MODEL_DIR / "indobert"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--allow-unreviewed", action="store_true")
    ap.add_argument("--epochs", type=int, default=4)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--lr", type=float, default=3e-5)
    ap.add_argument("--max-len", type=int, default=96)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    import torch
    from torch.utils.data import DataLoader
    from transformers import (
        AutoModelForSequenceClassification,
        AutoTokenizer,
        get_linear_schedule_with_warmup,
    )

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cpu":
        print("PERINGATAN: tidak ada GPU, training akan sangat lambat.", file=sys.stderr)

    rows, paraphrases = read_rows(DATASET), read_rows(PARAPHRASE)
    unreviewed = check_reviewed(rows, args.allow_unreviewed)
    split = {s: [r for r in rows if r["split"] == s] for s in ("train", "val", "test")}
    label_id = {lbl: i for i, lbl in enumerate(LABELS)}

    tok = AutoTokenizer.from_pretrained(CHECKPOINT)
    model = AutoModelForSequenceClassification.from_pretrained(
        CHECKPOINT,
        num_labels=len(LABELS),
        id2label=dict(enumerate(LABELS)),
        label2id=label_id,
    ).to(device)

    def encode(batch):
        enc = tok(
            [r["prompt"] for r in batch],
            padding=True,
            truncation=True,
            max_length=args.max_len,
            return_tensors="pt",
        )
        enc["labels"] = torch.tensor([label_id[r["intent"]] for r in batch])
        return enc

    loader = DataLoader(split["train"], batch_size=args.batch, shuffle=True, collate_fn=encode)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.01)
    steps = len(loader) * args.epochs
    sched = get_linear_schedule_with_warmup(opt, int(0.1 * steps), steps)

    model.train()
    for epoch in range(args.epochs):
        total = 0.0
        for batch in loader:
            batch = {k: v.to(device) for k, v in batch.items()}
            loss = model(**batch).loss
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            sched.step()
            opt.zero_grad()
            total += float(loss)
        print(f"epoch {epoch + 1}/{args.epochs} loss {total / len(loader):.4f}")

    @torch.no_grad()
    def proba(data):
        model.eval()
        out = []
        for i in range(0, len(data), 64):
            enc = tok(
                [r["prompt"] for r in data[i : i + 64]],
                padding=True,
                truncation=True,
                max_length=args.max_len,
                return_tensors="pt",
            ).to(device)
            out.append(torch.softmax(model(**enc).logits, dim=-1).cpu().numpy())
        return np.concatenate(out)

    val_p = proba(split["val"])
    threshold, sweep = choose_threshold(val_p, LABELS, [r["intent"] for r in split["val"]])
    test_pred = apply_threshold(proba(split["test"]), LABELS, threshold)
    para_pred = apply_threshold(proba(paraphrases), LABELS, threshold)

    experiment = unreviewed > 0
    version = f"intent-indobert-{date.today():%Y%m%d}"
    report = {
        "model_version": version,
        "checkpoint": CHECKPOINT,
        "hyperparameters": vars(args),
        "trained_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "experiment_unreviewed_rows": unreviewed,
        "status": "EKSPERIMEN (dataset belum diperiksa)" if experiment else "final",
        "counts": {k: len(v) for k, v in split.items()} | {"paraphrase": len(paraphrases)},
        "threshold": threshold,
        "threshold_sweep_val": sweep,
        "val": scores(
            [r["intent"] for r in split["val"]], apply_threshold(val_p, LABELS, threshold)
        ),
        "test": scores([r["intent"] for r in split["test"]], test_pred),
        "paraphrase": scores([r["intent"] for r in paraphrases], para_pred),
        "paraphrase_errors": [
            {"prompt": r["prompt"], "label": r["intent"], "pred": p}
            for r, p in zip(paraphrases, para_pred, strict=True)
            if r["intent"] != p
        ],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(OUT)
    tok.save_pretrained(OUT)
    save_report("indobert", report)
    plot_confusion(
        report["test"]["confusion"],
        REPO / "docs" / "eval" / "intent_confusion_indobert.png",
        f"Intent IndoBERT, set uji ({'EKSPERIMEN' if experiment else 'final'})",
    )
    print(
        f"{version}: uji macro F1 {report['test']['macro_f1']:.3f}, "
        f"parafrase macro F1 {report['paraphrase']['macro_f1']:.3f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
