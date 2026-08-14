from pathlib import Path

replacements = {
    "tests/test_v32_trace_conformance.py": [
        ('assert __version__=="0.49.0"', 'assert __version__=="0.50.0"'),
    ],
    "tests/test_v37_reasoning.py": [
        ('assert __version__ == "0.49.0"', 'assert __version__ == "0.50.0"'),
        ('assert report["contract"]["contract_version"] == "0.25.0"', 'assert report["contract"]["contract_version"] == "0.26.0"'),
    ],
    "tests/test_v38_semantic_dependencies.py": [
        ('assert __version__ == "0.49.0"', 'assert __version__ == "0.50.0"'),
        ('assert report["contract"]["contract_version"] == "0.25.0"', 'assert report["contract"]["contract_version"] == "0.26.0"'),
    ],
    "tests/test_v39_typed_capabilities.py": [
        ('assert __version__ == "0.49.0"', 'assert __version__ == "0.50.0"'),
        ('assert report["contract"]["contract_version"] == "0.25.0"', 'assert report["contract"]["contract_version"] == "0.26.0"'),
    ],
}

for path, pairs in replacements.items():
    p = Path(path)
    text = p.read_text()
    for old, new in pairs:
        count = text.count(old)
        if count != 1:
            raise SystemExit(f"{path}: expected exactly one {old!r}, found {count}")
        text = text.replace(old, new, 1)
    p.write_text(text)
