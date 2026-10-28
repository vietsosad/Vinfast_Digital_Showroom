import json
from pathlib import Path

from src.main import app

SNAPSHOT = Path(__file__).resolve().parents[2] / "docs" / "openapi.json"


def test_committed_openapi_matches_runtime():
    """Regenerate with: python scripts/export_openapi.py"""
    assert SNAPSHOT.is_file(), "docs/openapi.json is missing; run scripts/export_openapi.py"
    committed = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    assert committed == json.loads(json.dumps(app.openapi())), "docs/openapi.json is stale"
