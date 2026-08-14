from pathlib import Path
import runpy

p = Path("scripts/_promote_v51_once.py")
text = p.read_text()
bad = 'p = Path("README.md")n = p.read_text()'
good = 'p = Path("README.md")\nn = p.read_text()'
if bad not in text:
    raise SystemExit("expected v0.51 promotion syntax defect is not present")
p.write_text(text.replace(bad, good, 1))
runpy.run_path(str(p), run_name="__main__")

# Advance only current-public identity sentinels in the frozen v0.49 RC tests.
# v0.49 module identity and behavior assertions remain unchanged.
p = Path("tests/test_v49_rc.py")
text = p.read_text()
replacements = [
    ('assert __version__ == "0.50.0"', 'assert __version__ == "0.51.0"'),
    ('assert public["contract"]["contract_version"] == "0.26.0"', 'assert public["contract"]["contract_version"] == "0.27.0"'),
    ('assert first["runtime_version"] == "0.50.0"', 'assert first["runtime_version"] == "0.51.0"'),
    ('assert first["adoption_contract_version"] == "0.26.0"', 'assert first["adoption_contract_version"] == "0.27.0"'),
    ('assert report["freeze_manifest"]["runtime_version"] == "0.50.0"', 'assert report["freeze_manifest"]["runtime_version"] == "0.51.0"'),
]
for old, new in replacements:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"test_v49_rc.py: expected one {old!r}, found {count}")
    text = text.replace(old, new, 1)
p.write_text(text)
