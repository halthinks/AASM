from pathlib import Path

source_path = Path("scripts/_promote_v50_once.py")
source = source_path.read_text()
workflow_edit = '''# Release workflow: v0.50 requires the dedicated proof gate too.\nreplace_once(\n    ".github/workflows/release.yml",\n    "for context in aasm/ci-summary aasm/formal-assurance aasm/semantic-solver-rc; do",\n    "for context in aasm/ci-summary aasm/formal-assurance aasm/semantic-solver-rc aasm/proof-claims; do",\n)\n\n'''
if workflow_edit not in source:
    raise SystemExit("release workflow promotion block not found")
source = source.replace(workflow_edit, "", 1)
exec(compile(source, str(source_path), "exec"), {"__name__": "__main__"})

# The release contract deliberately expects aasm/proof-claims in release.yml.
# That single workflow edit is applied later through the GitHub connector, so
# the intermediate promotion commit cannot become releasable.
p = Path("README.md")
text = p.read_text()
old = "- **Proof Claims** exact binding, proof applicability, adversarial rejection, public CLI, replay, and conformance;"
new = "- **Proof Claims** exact binding, proof applicability, adversarial rejection, public CLI, replay, and conformance; publishes exact-head `aasm/proof-claims`;"
if old not in text:
    raise SystemExit("README Proof Claims verification bullet missing")
p.write_text(text.replace(old, new, 1))
