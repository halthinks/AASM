import json
from pathlib import Path


def test_all_json_schemas_parse():
    root = Path(__file__).resolve().parents[1]
    for path in (root / "schemas").glob("*.json"):
        data = json.loads(path.read_text())
        assert data["$schema"].startswith("https://json-schema.org/")
