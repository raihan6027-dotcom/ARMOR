"""Write the backend OpenAPI schema for the typed frontend client.

python scripts/export_openapi.py            # -> ../app/src/lib/api/openapi.json
cd ../app && npm run gen:api                # -> src/lib/api/schema.d.ts
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "app" / "src" / "lib" / "api" / "openapi.json"


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(app.openapi(), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"OpenAPI -> {OUT}")


if __name__ == "__main__":
    main()
