from pathlib import Path
import runpy

runpy.run_path("scripts/_promote_v50_once.py", run_name="__main__")

p = Path("README.md")
text = p.read_text()
old = "- **Proof Claims** exact binding, proof applicability, adversarial rejection, public CLI, replay, and conformance;"
new = "- **Proof Claims** exact binding, proof applicability, adversarial rejection, public CLI, replay, and conformance; publishes exact-head `aasm/proof-claims`;"
if old not in text:
    raise SystemExit("README Proof Claims verification bullet missing")
p.write_text(text.replace(old, new, 1))
