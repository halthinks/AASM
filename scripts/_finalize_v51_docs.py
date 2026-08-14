from pathlib import Path

p = Path("README.md")
text = p.read_text()
replacements = [
    ("**Next release:** v0.51.0 — Governed Solution Pools & Complete Enumeration", "**Next release:** v0.52.0 — Lexicographic Multi-Objective & Pareto Solving"),
    ("package / public surface: 0.50.0", "package / public surface: 0.51.0"),
    ("v0.50 adds proof-carrying solver claims as a thin layer over the v0.49 release-candidate runtime. Solver status remains Evidence; only an independent passing checker can label an exact-bound claim `PROOF_CERTIFIED`, and that certificate still does not become policy or truth authority.",
     "v0.51 adds governed solution pools and complete finite enumeration as a thin layer over the v0.50 proof runtime. Partial pools remain Evidence; `COMPLETE` requires durable finite-space exhaustion plus an independent exact-set certificate, and neither a pool nor its certificate becomes policy or truth authority."),
]
for old, new in replacements:
    if old not in text:
        raise SystemExit(f"README finalization anchor missing: {old}")
    text = text.replace(old, new, 1)
needle = "aasm.adoption.v1 / 0.27.0\n"
addition = "aasm.optimization.solution-pool.v1 / 0.1.0\naasm.optimization.enumeration.v1 / 0.1.0\n"
if addition not in text:
    if needle not in text:
        raise SystemExit("README adoption contract anchor missing")
    text = text.replace(needle, needle + addition, 1)
p.write_text(text)
