"""Risk AI scenarios: realistic combinations of content features for annotation.

    python ml/risk/scenarios.py          # -> ml/risk/data/scenarios.csv + empty annotation sheets

Each scenario is one row of the Risk AI feature schema (backend/app/ai/risk_features.py)
plus a short Indonesian description so annotators judge a concrete situation, not a
vector. Combinations are sampled with realistic dependencies (a personal edit is
usually about oneself, satire is usually stylized, synthetic voices only occur in
audio and video, political content is often in a sensitive context).

Consent and permission are deliberately absent: they are not risk features.
"""

from __future__ import annotations

import csv
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "backend"))

from app.ai.risk_features import HIGH, LOW, MID  # noqa: E402

SEED = 20260930
N_SCENARIOS = 600
DATA = HERE / "data"
SCENARIOS = DATA / "scenarios.csv"
ANNOTATION_DIR = HERE / "annotations"
FIELDS = [
    "scenario_id",
    "intent",
    "confidence",
    "target_type",
    "media",
    "realism",
    "manipulation",
    "sensitive_context",
    "synthetic_voice",
    "deskripsi",
]

INTENT_WEIGHTS = {
    "PERSONAL_CREATION": 12,
    "PERSONAL_EDITING": 12,
    "SATIRE_PARODY": 10,
    "COMMERCIAL_USE": 11,
    "POLITICAL_USE": 10,
    "IMPERSONATION": 10,
    "DEFAMATION": 10,
    "SEXUAL_EXPLICIT": 7,
    "DECEPTIVE": 10,
    "UNCERTAIN": 8,
}
INTENT_ID = {
    "PERSONAL_CREATION": "membuat karya pribadi (avatar, ilustrasi, narasi)",
    "PERSONAL_EDITING": "mengedit ringan (pencahayaan, latar, bising)",
    "SATIRE_PARODY": "membuat satire atau parodi",
    "COMMERCIAL_USE": "membuat iklan atau promosi",
    "POLITICAL_USE": "membuat materi kampanye atau dukungan politik",
    "IMPERSONATION": "membuat orang seolah mengatakan atau melakukan sesuatu",
    "DEFAMATION": "membuat orang terlihat bersalah atau tercela",
    "SEXUAL_EXPLICIT": "membuat konten seksual",
    "DECEPTIVE": "menipu atau menyebar kabar palsu",
    "UNCERTAIN": "tujuan tidak jelas",
}
TARGET_ID = {
    "SELF": "wajah/suara requester sendiri",
    "OTHER_REGISTERED": "orang lain yang terdaftar di ARMOR",
    "OTHER_UNREGISTERED": "orang lain yang tidak terdaftar",
    "UNCLEAR": "wajah/suara yang tidak jelas",
    "NONE": "tanpa orang",
}
MEDIA_ID = {"IMAGE": "gambar", "VIDEO": "video", "AUDIO": "audio", "TEXT_ONLY": "teks saja"}
LEVEL_ID = {LOW: "rendah", MID: "sedang", HIGH: "tinggi"}


def _pick(rng: random.Random, weights: dict):
    return rng.choices(list(weights), weights=list(weights.values()))[0]


def sample(rng: random.Random) -> dict:
    intent = _pick(rng, INTENT_WEIGHTS)
    personal = intent in ("PERSONAL_CREATION", "PERSONAL_EDITING")
    target = _pick(
        rng,
        {"SELF": 6, "OTHER_REGISTERED": 1, "OTHER_UNREGISTERED": 2, "UNCLEAR": 1, "NONE": 1}
        if personal
        else {"SELF": 1, "OTHER_REGISTERED": 4, "OTHER_UNREGISTERED": 5, "UNCLEAR": 2, "NONE": 1},
    )
    media = _pick(rng, {"IMAGE": 5, "VIDEO": 3, "AUDIO": 3, "TEXT_ONLY": 1})
    if intent == "SATIRE_PARODY":
        realism = _pick(rng, {LOW: 6, MID: 2, HIGH: 2})
    elif intent in ("IMPERSONATION", "DECEPTIVE", "DEFAMATION"):
        realism = _pick(rng, {LOW: 1, MID: 3, HIGH: 5})
    else:
        realism = _pick(rng, {LOW: 3, MID: 5, HIGH: 2})
    if intent == "PERSONAL_EDITING":
        manipulation = _pick(rng, {LOW: 7, MID: 2, HIGH: 1})
    elif intent in ("IMPERSONATION",):
        manipulation = _pick(rng, {LOW: 0.5, MID: 2, HIGH: 7})
    else:
        manipulation = _pick(rng, {LOW: 2, MID: 5, HIGH: 3})
    sens_p = {"POLITICAL_USE": 0.6, "DECEPTIVE": 0.6, "DEFAMATION": 0.3}.get(intent, 0.12)
    sensitive = int(rng.random() < sens_p)
    synthetic = int(
        media in ("AUDIO", "VIDEO")
        and rng.random() < (0.5 if intent in ("IMPERSONATION", "DECEPTIVE") else 0.15)
    )
    confidence = round(
        rng.uniform(0.25, 0.6) if intent == "UNCERTAIN" else rng.uniform(0.5, 0.99), 2
    )
    desc = (
        f"Permintaan {MEDIA_ID[media]} untuk {INTENT_ID[intent]}, melibatkan {TARGET_ID[target]}. "
        f"Realisme {LEVEL_ID[realism]}, tingkat manipulasi {LEVEL_ID[manipulation]}"
        + (
            ", konteks sensitif (anak, agama, pemilu, bencana, keuangan, atau hukum)"
            if sensitive
            else ""
        )
        + (", terdeteksi suara sintetis" if synthetic else "")
        + f". Keyakinan model intent {confidence:.2f}."
    )
    return {
        "intent": intent,
        "confidence": confidence,
        "target_type": target,
        "media": media,
        "realism": realism,
        "manipulation": manipulation,
        "sensitive_context": sensitive,
        "synthetic_voice": synthetic,
        "deskripsi": desc,
    }


def build(n: int = N_SCENARIOS, seed: int = SEED) -> list[dict]:
    rng = random.Random(seed)
    rows, seen = [], set()
    while len(rows) < n:
        s = sample(rng)
        key = tuple(s[k] for k in FIELDS[1:9])
        if key in seen:
            continue
        seen.add(key)
        rows.append({"scenario_id": f"RSK-{len(rows) + 1:04d}", **s})
    return rows


def write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main() -> int:
    rows = build()
    write_csv(SCENARIOS, FIELDS, rows)
    sheet = [
        {"scenario_id": r["scenario_id"], "deskripsi": r["deskripsi"], "label": "", "catatan": ""}
        for r in rows
    ]
    for who in ("anotator_A", "anotator_B"):
        path = ANNOTATION_DIR / f"{who}.csv"
        if path.exists() and any(r["label"] for r in csv.DictReader(path.open(encoding="utf-8"))):
            print(f"{path.name} sudah berisi label; tidak ditimpa.")
            continue
        write_csv(path, ["scenario_id", "deskripsi", "label", "catatan"], sheet)
    print(f"{len(rows)} skenario -> {SCENARIOS}; lembar anotasi di {ANNOTATION_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
