from pathlib import Path

FILES = [
    "tests/test_v32_trace_conformance.py",
    "tests/test_v37_reasoning.py",
    "tests/test_v38_semantic_dependencies.py",
    "tests/test_v39_typed_capabilities.py",
    "tests/test_v40_hierarchical_memory.py",
    "tests/test_v42_reference_domains.py",
    "tests/test_v44_optimization.py",
    "tests/test_v45_public.py",
    "tests/test_v46_public.py",
    "tests/test_v47_public.py",
    "tests/test_v48_public.py",
    "tests/test_v49_rc_real.py",
]

for name in FILES:
    p = Path(name)
    text = p.read_text()
    if "0.50.0" not in text:
        raise SystemExit(f"{name}: expected current-public 0.50.0 sentinel")
    text = text.replace("0.50.0", "0.51.0")
    text = text.replace("0.26.0", "0.27.0")
    text = text.replace("under_v50", "under_v51")
    text = text.replace("under v50", "under v51")
    text = text.replace("under_v50_composition", "under_v51_composition")
    text = text.replace("v0.50 here", "v0.51 here")
    p.write_text(text)

p = Path(".github/workflows/rc.yml")
text = p.read_text()
old = 'if report["freeze_manifest"]["runtime_version"] != "0.50.0":\n              raise SystemExit("RC freeze manifest is not the current v0.50 public contract")'
new = 'if report["freeze_manifest"]["runtime_version"] != "0.51.0":\n              raise SystemExit("RC freeze manifest is not the current v0.51 public contract")'
if old not in text:
    raise SystemExit("rc.yml: expected current v0.50 freeze sentinel")
p.write_text(text.replace(old, new, 1))
