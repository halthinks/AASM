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
