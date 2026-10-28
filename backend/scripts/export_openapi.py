"""Write the runtime OpenAPI document to docs/openapi.json.

    python scripts/export_openapi.py

tests/test_openapi_snapshot.py fails when the committed file differs from the
running application, so the published contract can never drift from the code.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
OUTPUT = BACKEND_ROOT.parent / "docs" / "openapi.json"
sys.path.insert(0, str(BACKEND_ROOT))


def render() -> str:
    os.environ.setdefault("APP_ENV", "test")
    from src.main import app

    return json.dumps(app.openapi(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main() -> None:
    OUTPUT.write_text(render(), encoding="utf-8", newline="\n")
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
