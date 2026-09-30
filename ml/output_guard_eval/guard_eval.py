"""Output Guard evaluation (CLAUDE.md Lampiran C: "persentase hasil terlarang yang tertahan").

Uses the volunteer photos collected for ml/face_eval (never committed):

    ml/face_eval/data/relawan/<KODE>/enroll/*.jpg   3 enrollment photos
    ml/face_eval/data/relawan/<KODE>/probe/*.jpg    other photos

Every volunteer is enrolled with the backend's own enrollment check. Then, for
ordered pairs (requester R, other volunteer V):

  forbidden output  R's photo, edited by generator_mock in test mode inject_face with
                    a probe photo of V pasted in. V never allowed this, so the
                    Output Guard must hold it.
  allowed output    R's photo, edited by generator_mock without injection. Only R's
                    own face is in it, so it must pass (a hold here is a false alarm).

Faces are found by the real Face AI (InsightFace buffalo_l) and judged by
app.services.output_guard.judge, the exact rule the backend runs.

    python ml/output_guard_eval/guard_eval.py                 # -> docs/eval/output-guard.md
    python ml/output_guard_eval/guard_eval.py --max-pairs 200
"""

from __future__ import annotations

import argparse
import itertools
import random
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "generator_mock"))

DATA = REPO / "ml" / "face_eval" / "data" / "relawan"
REPORT = REPO / "docs" / "eval" / "output-guard.md"
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
PROMPT = "Cerahkan foto ini."


def images(folder: Path) -> list[Path]:
    if not folder.exists():
        return []
    return sorted(p for p in folder.iterdir() if p.suffix.lower() in IMAGE_EXT)


@dataclass
class Tally:
    total: int = 0
    held: int = 0
    reasons: dict[str, int] = field(default_factory=dict)

    def add(self, passed: bool, reasons: list[str]) -> None:
        self.total += 1
        if not passed:
            self.held += 1
            for r in set(reasons):
                self.reasons[r] = self.reasons.get(r, 0) + 1

    @property
    def rate(self) -> float:
        return self.held / self.total if self.total else 0.0


def run(pairs, generate, analyze, judge, index) -> tuple[Tally, Tally]:
    """pairs: (requester_code, requester_photo_bytes, victim_photo_bytes or None).
    Returns (forbidden, allowed) tallies."""
    forbidden, allowed = Tally(), Tally()
    for requester, base, victim in pairs:
        output = generate(PROMPT, base, victim)
        result = judge(analyze(output), requester, index, set())
        (forbidden if victim is not None else allowed).add(result.passed, result.reasons)
    return forbidden, allowed


def pct(x: float) -> str:
    return f"{x * 100:.1f}%".replace(".", ",")


def report(forbidden: Tally, allowed: Tally, people: int, skipped: list[str], settings) -> str:
    lines = [
        "# Evaluasi Output Guard",
        "",
        f"Dijalankan: {date.today().isoformat()} dengan `ml/output_guard_eval/guard_eval.py`.",
        f"Relawan terdaftar: {people}. Ambang wajah: {settings.face_match_threshold} "
        f"(margin abu-abu {settings.face_gray_margin}).",
        "",
        "| Jenis hasil | Jumlah | Ditahan | Persentase ditahan |",
        "| --- | --- | --- | --- |",
        f"| Terlarang (memuat wajah relawan lain tanpa izin) | {forbidden.total} | "
        f"{forbidden.held} | {pct(forbidden.rate)} |",
        f"| Diizinkan (hanya wajah requester) | {allowed.total} | {allowed.held} | "
        f"{pct(allowed.rate)} (alarm palsu) |",
        "",
        "Alasan penahanan hasil terlarang: "
        + (", ".join(f"{k} {v}" for k, v in sorted(forbidden.reasons.items())) or "-"),
        "",
        "Alasan penahanan hasil yang diizinkan: "
        + (", ".join(f"{k} {v}" for k, v in sorted(allowed.reasons.items())) or "-"),
        "",
        "Generator: `generator_mock` (simulasi). Hasil dengan model generatif sungguhan bisa "
        "berbeda karena wajah ikut diubah oleh model.",
    ]
    if skipped:
        lines += ["", "Relawan yang tidak bisa didaftarkan (dilewati): " + ", ".join(skipped)]
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--data", type=Path, default=DATA)
    ap.add_argument("--max-pairs", type=int, default=400)
    ap.add_argument("--out", type=Path, default=REPORT)
    args = ap.parse_args()

    from armor_generator_mock.transforms import generate as mock_generate

    from app.ai.face import face_ai
    from app.core.config import settings
    from app.core.exceptions import ArmorError
    from app.services.identity_service import check_enrollment_captures
    from app.services.output_guard import judge

    if not face_ai.available:
        print(f"Model wajah tidak tersedia: {face_ai.init_error}", file=sys.stderr)
        return 2
    if not args.data.exists():
        print(f"Folder data tidak ada: {args.data}. Lihat ml/face_eval/README.md.", file=sys.stderr)
        return 2

    index, probes, skipped = [], {}, []
    for person in sorted(p for p in args.data.iterdir() if p.is_dir()):
        enroll = [p.read_bytes() for p in images(person / "enroll")]
        try:
            mean = check_enrollment_captures(enroll)
        except ArmorError as exc:
            skipped.append(f"{person.name} ({exc.code})")
            continue
        ident = SimpleNamespace(identity_id=person.name, user_id=person.name, is_child=False)
        index.append((ident, mean))
        probes[person.name] = [p.read_bytes() for p in images(person / "probe")]
    people = [k for k, v in probes.items() if v]
    if len(people) < 2:
        print("Butuh minimal 2 relawan dengan foto probe.", file=sys.stderr)
        return 2

    rng = random.Random(16)  # fixed: the same pairs every run
    pairs = list(itertools.permutations(people, 2))
    rng.shuffle(pairs)
    trials = []
    for r, v in pairs[: args.max_pairs]:
        base = rng.choice(probes[r])
        trials.append((r, base, rng.choice(probes[v])))
        trials.append((r, base, None))

    forbidden, allowed = run(
        trials,
        lambda prompt, base, inject: mock_generate(prompt, base, inject).png,
        face_ai.analyze,
        judge,
        index,
    )
    args.out.write_text(report(forbidden, allowed, len(index), skipped, settings), encoding="utf-8")
    print(
        f"terlarang ditahan {forbidden.held}/{forbidden.total}; "
        f"alarm palsu {allowed.held}/{allowed.total} -> {args.out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
