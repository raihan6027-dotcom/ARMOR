"""Hasilkan rahasia baru untuk .env: JWT_SECRET dan ARMOR_EMBEDDING_KEY.

Pemakaian:
    python scripts/gen_secrets.py            # cetak ke layar
    python scripts/gen_secrets.py --write    # isi/ganti nilai kosong di backend/.env

Nilai tidak pernah ditulis ke file lain dan tidak boleh di-commit.
"""

from __future__ import annotations

import argparse
import re
import secrets
from pathlib import Path

from cryptography.fernet import Fernet

_PLACEHOLDERS = ("", "ganti-dengan-hasil-gen-secrets", "change-me-in-production")
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


def generate() -> dict[str, str]:
    return {
        "JWT_SECRET": secrets.token_urlsafe(48),
        "ARMOR_EMBEDDING_KEY": Fernet.generate_key().decode(),
    }


def write_env(values: dict[str, str], path: Path = ENV_PATH) -> list[str]:
    """Isi kunci yang kosong atau masih placeholder. Kunci yang sudah terisi tidak
    diganti, karena mengganti ARMOR_EMBEDDING_KEY membuat embedding lama tak terbaca."""
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    changed = []
    for key, val in values.items():
        pattern = re.compile(rf"^{key}=(.*)$", re.MULTILINE)
        m = pattern.search(text)
        if m is None:
            text += ("" if text.endswith("\n") or not text else "\n") + f"{key}={val}\n"
            changed.append(key)
        elif m.group(1).strip() in _PLACEHOLDERS:
            text = pattern.sub(f"{key}={val}", text, count=1)
            changed.append(key)
    path.write_text(text, encoding="utf-8")
    return changed


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write", action="store_true", help="tulis ke backend/.env")
    args = ap.parse_args()
    values = generate()
    if args.write:
        changed = write_env(values)
        filled = ", ".join(changed) if changed else "(tidak ada, semua sudah terisi)"
        print("Diisi di .env:", filled)
    else:
        for k, v in values.items():
            print(f"{k}={v}")


if __name__ == "__main__":
    main()
